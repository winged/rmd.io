from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from mails.models import Mail, Statistic, Recipient
from lockfile import FileLock
from mails import imaphelper, tools
from mails.models import ImportLog
import datetime
import logging

logger = logging.getLogger('mails')

class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def import_mail(self, message):

        try:
            sender        = message.get_sender()
            recipients    = message.get_recipients()
            subject       = message.get_subject()
            sent_date     = message.get_sent_date()
            delay_address = tools.get_delay_address_from_recipients(recipients)
            key           = tools.get_key_from_email_address(delay_address)
            due_date      = sent_date + datetime.timedelta(
                tools.get_delay_days_from_email_address(delay_address)
            )
        except Exception as e:
            message.delete()
            logger.error('Mail from %s deleted: Failed to parse header, %s' % (sender, e.args[0]))

            return

        try:
            user = User.objects.get(
                email=sender,
                is_active=True
            )
            account = user.get_account()
        except:
            message.delete()
            logger.error('Mail from %s deleted: User not registered' % sender)
            tools.send_registration_mail(sender)

            return

        if account.anti_spam:
            if not key:
                message.delete()
                logger.error('Mail from %s deleted: No key' % sender)
                tools.send_wrong_recipient_mail(sender)

                return
            elif key != account.key:
                message.delete()
                logger.error('Mail from %s deleted: Wrong key' % sender)

                return

        try:
            mail = Mail(
                subject=subject,
                sent=sent_date,
                due=due_date,
                user=user,
            )
            rec_stat = Statistic(
                type='REC',
                email=delay_address
            )
            user_stat = Statistic(
                type='USER',
                email=user.email,
            )
            mail.save()
            rec_stat.save()
            user_stat.save()

            for i in recipients:
                recipient = Recipient(
                    mail=mail,
                    email=recipients[i]['email'],
                    name=recipients[i]['name']
                )
                recipient.save()
                if recipients[i]['email'] != delay_address:
                    obl_stat = Statistic(
                        type='OBL',
                        email=recipients[i]['email']
                    )
                    obl_stat.save()
                else:
                    continue

            message.flag(mail.id)
        except:
            message.delete()
            logger.error('Mail from %s deleted: Could not save mail' % sender)

            return

    def handle(self, *args, **kwargs):

        lock = FileLock('/tmp/lockfile.tmp')
        with lock:

            last_import, created = ImportLog.objects.get_or_create()
            import_diff = timezone.now() - last_import.date

            if import_diff > datetime.timedelta(seconds=30):
                last_import.save()
            else:
                return

            imap_conn = imaphelper.get_connection()
            messages = imaphelper.get_unflagged(imap_conn)

            for message in messages:
                self.import_mail(message)

            imap_conn.expunge()
