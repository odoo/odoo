import base64

from markupsafe import Markup
from unittest.mock import patch

from odoo import SUPERUSER_ID
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.models.mail_test_access import MailTestAccess
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.exceptions import AccessError
from odoo.tools import mute_logger
from odoo.tests import HttpCase, tagged


class MessageAccessCommon(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_public = mail_new_test_user(
            cls.env,
            groups='base.group_public',
            login='bert',
            name='Bert Tartignole',
        )
        cls.user_portal = mail_new_test_user(
            cls.env,
            groups='base.group_portal',
            login='chell',
            name='Chell Gladys',
        )
        cls.user_portal_2 = mail_new_test_user(
            cls.env,
            groups='base.group_portal',
            login='portal2',
            name='Chell Gladys',
        )

        cls.test_subtype_access_internal = cls.env['mail.message.subtype'].create([
            {
                'internal': True,
                'name': 'Test Internal',
            },
        ])

        (
            cls.record_public, cls.record_portal, cls.record_portal_ro,
            cls.record_followers,
            cls.record_internal, cls.record_internal_ro,
            cls.record_admin
        ) = cls.env['mail.test.access'].create([
            {'access': 'public', 'name': 'Public Record'},
            {'access': 'logged', 'name': 'Portal Record'},
            {'access': 'logged_ro', 'name': 'Portal RO Record'},
            {'access': 'followers', 'name': 'Followers Record'},
            {'access': 'internal', 'name': 'Internal Record'},
            {'access': 'internal_ro', 'name': 'Internal Readonly Record'},
            {'access': 'admin', 'name': 'Admin Record'},
        ])
        for record in (cls.record_public + cls.record_portal + cls.record_portal_ro + cls.record_followers +
                       cls.record_internal + cls.record_internal_ro + cls.record_admin):
            record.message_post(
                body='Test Comment',
                message_type='comment',
                subtype_id=cls.env.ref('mail.mt_comment').id,
            )
            record.message_post(
                body='Test Answer',
                message_type='comment',
                subtype_id=cls.env.ref('mail.mt_comment').id,
            )


@tagged('mail_message', 'security', 'post_install', '-at_install')
class TestMailMessageAccess(MessageAccessCommon):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_assert_initial_values(self):
        """ Just ensure tests data """
        for record in (
            self.record_public + self.record_portal + self.record_portal_ro + self.record_followers +
            self.record_internal + self.record_internal_ro + self.record_admin):
            self.assertFalse(record.message_follower_ids)
            self.assertEqual(len(record.message_ids), 3)

            for index, msg in enumerate(record.message_ids):
                body = ['<p>Test Answer</p>', '<p>Test Comment</p>', '<p>Mail Access Test created</p>'][index]
                message_type = ['comment', 'comment', 'notification'][index]
                subtype_id = [self.env.ref('mail.mt_comment'), self.env.ref('mail.mt_comment'), self.env.ref('mail.mt_note')][index]
                self.assertEqual(msg.author_id, self.partner_root)
                self.assertEqual(msg.body, body)
                self.assertEqual(msg.message_type, message_type)
                self.assertFalse(msg.notified_partner_ids)
                self.assertFalse(msg.partner_ids)
                self.assertEqual(msg.subtype_id, subtype_id)

        # public user access check
        for allowed in self.record_public:
            allowed.with_user(self.user_public).read(['name'])
        for forbidden in self.record_portal + self.record_portal_ro + self.record_followers + self.record_internal + self.record_internal_ro + self.record_admin:
            with self.assertRaises(AccessError):
                forbidden.with_user(self.user_public).read(['name'])
        for forbidden in self.record_public + self.record_portal + self.record_portal_ro + self.record_followers + self.record_internal + self.record_internal_ro + self.record_admin:
            with self.assertRaises(AccessError):
                forbidden.with_user(self.user_public).write({'name': 'Update'})

        # portal user access check
        for allowed in self.record_public + self.record_portal + self.record_portal_ro:
            allowed.with_user(self.user_portal).read(['name'])
        for forbidden in self.record_internal + self.record_internal_ro + self.record_admin:
            with self.assertRaises(AccessError):
                forbidden.with_user(self.user_portal).read(['name'])
        for allowed in self.record_portal:
            allowed.with_user(self.user_portal).write({'name': 'Update'})
        for forbidden in self.record_public + self.record_portal_ro + self.record_followers + self.record_internal + self.record_internal_ro + self.record_admin:
            with self.assertRaises(AccessError):
                forbidden.with_user(self.user_portal).write({'name': 'Update'})
        self.record_followers.message_subscribe(self.user_portal.partner_id.ids)
        self.record_followers.with_user(self.user_portal).read(['name'])
        self.record_followers.with_user(self.user_portal).write({'name': 'Update'})

        # internal user access check
        for allowed in self.record_public + self.record_portal + self.record_portal_ro + self.record_followers + self.record_internal + self.record_internal_ro:
            allowed.with_user(self.user_employee).read(['name'])
        for forbidden in self.record_admin:
            with self.assertRaises(AccessError):
                forbidden.with_user(self.user_employee).read(['name'])
        for allowed in self.record_public + self.record_portal + self.record_portal_ro + self.record_followers + self.record_internal:
            allowed.with_user(self.user_employee).write({'name': 'Update'})
        for forbidden in self.record_internal_ro + self.record_admin:
            with self.assertRaises(AccessError):
                forbidden.with_user(self.user_employee).write({'name': 'Update'})

        # elevated user access check
        for allowed in self.record_public + self.record_portal + self.record_portal_ro + self.record_followers + self.record_internal + self.record_internal_ro + self.record_admin:
            allowed.with_user(self.user_admin).read(['name'])

    # ------------------------------------------------------------
    # CREATE
    # - Criterions
    #  - "private message" (no model, no res_id) -> deprecated
    #  - follower of document
    #  - document-based (write or create, using '_get_mail_message_access'
    #    hence '_mail_post_access' by default)
    #  - notified of parent message
    # ------------------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_create(self):
        """ Test 'group_user' creation rules """
        # prepare 'notified of parent' condition
        admin_msg = self.record_admin.message_ids[0]
        admin_msg.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})

        # prepare 'followers' condition
        record_admin_fol = self.env['mail.test.access'].create({
            'access': 'admin',
            'name': 'Admin Record Follower',
        })
        record_admin_fol.message_subscribe(self.user_employee.partner_id.ids)

        for record, msg_vals, should_crash, reason in [
            # private-like
            (self.env["mail.test.access"], {}, False, 'Private message like is ok'),
            # document based
            (self.record_internal, {}, False, 'W Access on record'),
            (self.record_internal, {'message_type': 'notification'}, False, 'W Access on record, notification does not change anything'),
            (self.record_internal_ro, {}, True, 'No W Access on record'),
            (self.record_admin, {}, True, 'No access on record (and not notified on first message)'),
            (record_admin_fol, {
                'reply_to': 'avoid.catchall@my.test.com',  # otherwise crashes
            }, False, 'Followers > no access on record'),
            # parent based
            (self.record_admin, {  # note: force reply_to normally computed by message_post avoiding ACLs issues
                'parent_id': admin_msg.id,
            }, False, 'No access on record but reply to notified parent'),
        ]:
            with self.subTest(record=record, msg_vals=msg_vals, reason=reason):
                final_vals = dict(
                    {
                        'body': 'Test',
                        'message_type': 'comment',
                        'subtype_id': self.env.ref('mail.mt_comment').id,
                    }, **msg_vals
                )
                if should_crash:
                    with self.assertRaises(AccessError):
                        self.env['mail.message'].with_user(self.user_employee).create({
                            'model': record._name if record else False,
                            'res_id': record.id if record else False,
                            **final_vals,
                        })
                    if record:
                        with self.assertRaises(AccessError):
                            record.with_user(self.user_employee).message_post(
                                **final_vals,
                            )
                else:
                    _message = self.env['mail.message'].with_user(self.user_employee).create({
                        'model': record._name if record else False,
                        'res_id': record.id if record else False,
                        **final_vals,
                    })
                    if record:
                        # TDE note: due to parent_id flattening, doing message_post
                        # with parent_id which should allow posting crashes, as
                        # parent_id is changed to an older message the employee cannot
                        # access. Won't fix that in stable.
                        if record == self.record_admin and 'parent_id' in msg_vals:
                            continue
                        record.with_user(self.user_employee).message_post(
                            **final_vals,
                        )

    def test_access_create_customized(self):
        """ Test '_get_mail_message_access' support """
        record = self.env['mail.test.access.custo'].with_user(self.user_employee).create({'name': 'Open'})
        for user in self.user_employee + self.user_portal:
            with self.subTest(user_name=user.name):
                _message = record.with_user(user).message_post(
                    attachments=[('Attachment', b'My attachment')],
                    body='A message',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )
        # lock -> see '_get_mail_message_access'
        record.write({'is_locked': True})
        record.invalidate_model()
        for user in self.user_employee + self.user_portal:
            with self.subTest(user_name=user.name):
                with self.assertRaises(AccessError):
                    _message = record.with_user(user).message_post(
                        body='Another portal message',
                        subtype_id=self.env.ref('mail.mt_comment').id,
                    )
        # readonly -> "read" access sufficient on unlocked records, see '_get_mail_message_access'
        record.sudo().write({'is_locked': False, 'is_readonly': True})
        record.invalidate_model()
        for user in self.user_employee + self.user_portal:
            with self.subTest(user_name=user.name):
                # cannot write
                with self.assertRaises(AccessError):
                    record.with_user(user).write({'name': 'Can Update'})
                # can post
                _message = record.with_user(user).message_post(
                    attachments=[('Attachment', b'My attachment')],
                    body='Another portal message',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )
                # controller check
                self.authenticate(user.login, user.login)
                res = self.make_jsonrpc_request(
                    route="/mail/message/post",
                    params={
                        'thread_model': record._name,
                        'thread_id': record.id,
                        'post_data': {
                            'body': "Test",
                        },
                    },
                )
                self.assertEqual(len(res['mail.message']), 1)

    def test_access_create_mail_post_access(self):
        """ Test 'mail_post_access' support that allows creating a message with
        other rights than 'write' access on document """
        for post_value, should_crash in [
            ('read', False),
            ('write', True),
        ]:
            with self.subTest(post_value=post_value):
                with patch.object(MailTestAccess, '_mail_post_access', post_value):
                    if should_crash:
                        with self.assertRaises(AccessError):
                            self.env['mail.message'].with_user(self.user_employee).create({
                                'model': self.record_internal_ro._name,
                                'res_id': self.record_internal_ro.id,
                                'body': 'Test',
                            })
                    else:
                        self.env['mail.message'].with_user(self.user_employee).create({
                            'model': self.record_internal_ro._name,
                            'res_id': self.record_internal_ro.id,
                            'body': 'Test',
                        })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_create_portal(self):
        """ Test group_portal creation rules """
        # prepare 'notified of parent' condition
        admin_msg = self.record_admin.message_ids[-1]
        admin_msg.write({'partner_ids': [(4, self.user_portal.partner_id.id)]})

        # prepare 'followers' condition
        record_admin_fol = self.env['mail.test.access'].create({
            'access': 'admin',
            'name': 'Admin Record',
        })
        record_admin_fol.message_subscribe(self.user_portal.partner_id.ids)

        for record, msg_vals, should_crash, reason in [
            # private-like
            (self.env["mail.test.access"], {}, False, 'Private message like is ok'),
            # document based
            (self.record_portal, {}, False, 'W Access on record'),
            (self.record_portal_ro, {}, True, 'No W Access on record'),
            (self.record_internal, {}, True, 'No R/W Access on record'),
            (record_admin_fol, {
                'reply_to': 'avoid.catchall@my.test.com',  # otherwise crashes
            }, False, 'Followers > no access on record'),
            # parent based
            (self.record_admin, {
                'parent_id': admin_msg.id,
            }, False, 'No access on record but reply to notified parent'),
            # internal = forbidden (internal users only)
            (self.record_portal, {'is_internal': True}, True, 'Internal subtype always forbidden'),
            (self.record_portal, {'is_internal': True, 'message_type': 'notification'}, False, 'Automatic log accepted'),
            (self.record_portal, {'subtype_id': self.env.ref('mail.mt_note').id}, True, 'Internal flag always forbidden'),
            (self.record_portal, {'subtype_id': self.test_subtype_access_internal.id}, True, 'Internal flag (custom subtype) always forbidden'),
            (self.record_portal, {'message_type': 'notification', 'subtype_id': self.test_subtype_access_internal.id}, False, 'Automatic log accepted'),
            (self.record_portal, {'subtype_id': False}, True, 'No subtype = internal = always forbidden'),
        ]:
            with self.subTest(record=record, msg_vals=msg_vals, reason=reason):
                if should_crash:
                    with self.assertRaises(AccessError):
                        self.env['mail.message'].with_user(self.user_portal).create({
                            'model': record._name if record else False,
                            'res_id': record.id if record else False,
                            'body': 'Test',
                            'message_type': 'comment',
                            'subtype_id': self.env.ref('mail.mt_comment').id,
                            **msg_vals,
                        })
                else:
                    _message = self.env['mail.message'].with_user(self.user_portal).create({
                        'model': record._name if record else False,
                        'res_id': record.id if record else False,
                        'body': 'Test',
                        'message_type': 'comment',
                        'subtype_id': self.env.ref('mail.mt_comment').id,
                        **msg_vals,
                    })

        # check '_mail_post_access', reducing W to R
        with patch.object(MailTestAccess, '_mail_post_access', 'read'):
            _message = self.env['mail.message'].with_user(self.user_portal).create({
                'model': self.record_portal._name,
                'res_id': self.record_portal.id,
                'body': 'Test',
                'subtype_id': self.env.ref('mail.mt_comment').id,
            })

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_access_create_public(self):
        """ Public can never create messages """
        for record in [
            self.env['mail.test.access'],  # old private message: no document
            self.record_public,  # read access
            self.record_portal,  # read access
        ]:
            with self.subTest(record=record):
                # can never create message, simple
                with self.assertRaises(AccessError):
                    self.env['mail.message'].with_user(self.user_public).create({
                        'model': record._name if record else False,
                        'res_id': record.id if record else False,
                        'body': 'Test',
                    })

    @mute_logger('odoo.tests')
    def test_access_create_wo_parent_access(self):
        """ Purpose is to test posting a message on a record whose first message / parent
        is not accessible by current user. This cause issues notably when computing
        references, checking ancestors message_ids. """
        test_record = self.env['mail.test.simple'].with_context(self._test_context).create({
            'email_from': 'ignasse@example.com',
            'name': 'Test',
        })
        partner_1 = self.env['res.partner'].create({
            'name': 'Not Jitendra Prajapati',
            'email': 'not.jitendra@mycompany.example.com',
        })
        test_record.message_subscribe((partner_1 | self.user_admin.partner_id).ids)

        message = test_record.message_post(
            body=Markup('<p>This is First Message</p>'),
            message_type='comment',
            subject='Subject',
            subtype_xmlid='mail.mt_note',
        )
        # portal user have no rights to read the message
        with self.assertRaises(AccessError):
            message.with_user(self.user_portal).read(['subject', 'body'])

        with patch.object(MailTestSimple, '_check_access', return_value=None):
            with self.assertRaises(AccessError):
                message.with_user(self.user_portal).read(['subject', 'body'])

            # parent message is accessible to references notification mail values
            # for _notify method and portal user have no rights to send the message for this model
            with self.mock_mail_gateway():
                new_msg = test_record.with_user(self.user_portal).message_post(
                    body='<p>This is Second Message</p>',
                    subject='Subject',
                    parent_id=message.id,
                    mail_auto_delete=False,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
            self.assertEqual(new_msg.sudo().parent_id, message)

        new_mail = self.env['mail.mail'].sudo().search([
            ('mail_message_id', '=', new_msg.id),
        ])
        self.assertEqual(
            new_mail.references, f'{message.message_id} {new_msg.message_id}',
            'References should not include message parent message_id, even if internal note, to help thread formation')
        self.assertTrue(new_mail)
        self.assertEqual(new_msg.parent_id, message)

    # ------------------------------------------------------------
    # READ
    # - Criterions
    #  - author
    #  - creator (might post on behalf of someone else)
    #  - recipients / notified
    #  - document-based: read, using '_get_mail_message_access'
    # - share users: limited to 'not internal' (flag or subtype)
    # ------------------------------------------------------------

    def test_access_read(self):
        """ Read access check for internal users. """
        for msg, msg_vals, should_crash, reason in [
            # document based
            (self.record_internal.message_ids[0], {}, False, 'R Access on record'),
            (self.record_internal_ro.message_ids[0], {}, False, 'R Access on record'),
            (self.record_admin.message_ids[0], {}, True, 'No access on record'),
            # author
            (self.record_admin.message_ids[0], {
                'author_id': self.user_employee.partner_id.id,
            }, False, 'Author > no access on record'),
            (self.record_admin.message_ids[0], {
                'create_uid': self.user_employee.id,
            }, False, 'Creator > no access on record'),
            # notified
            (self.record_admin.message_ids[0], {
                'notification_ids': [(0, 0, {
                    'res_partner_id': self.user_employee.partner_id.id,
                })],
            }, False, 'Notified > no access on record'),
            (self.record_admin.message_ids[0], {
                'partner_ids': [(4, self.user_employee.partner_id.id)],
            }, False, 'Recipients > no access on record'),
        ]:
            original_vals = {
                'author_id': msg.author_id.id,
                'notification_ids': [(6, 0, {})],
                'parent_id': msg.parent_id.id,
            }
            with self.subTest(msg=msg, reason=reason):
                if 'create_uid' in msg_vals:
                    self.patch(self.env.registry, 'ready', False)
                    msg.with_user(SUPERUSER_ID).write(msg_vals)
                    self.patch(self.env.registry, 'ready', True)
                    self.assertEqual(msg.create_uid.id, msg_vals['create_uid'])
                elif msg_vals:
                    msg.write(msg_vals)
                if should_crash:
                    with self.assertRaises(AccessError):
                        msg.with_user(self.user_employee).read(['body'])
                else:
                    msg.with_user(self.user_employee).read(['body'])
                if msg_vals:
                    msg.write(original_vals)

    def test_access_read_customized(self):
        """ Test '_get_mail_message_access' support """
        records = self.env['mail.test.access.custo'].with_user(self.user_admin).create([
            {'name': 'Open'},
            {'name': 'Open RO', 'is_readonly': True},
            {'is_locked': True, 'name': 'Locked'},
        ])
        messages_all = self.env['mail.message']
        for record in records:
            messages_all += record.with_user(self.user_admin).message_post(
                body=f'AnchorForTest / A message from {self.user_admin.name} on {record.name}',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
        # lock -> see '_get_mail_message_access', cannot read locked message
        # without write access, with is not granted for employees
        with self.assertRaises(AccessError):  # write access not granted on locked -> cannot read message
            messages_all[2].with_user(self.user_employee).read(['subject'])
        with self.assertRaises(AccessError):  # also working in case of batch ok / not ok
            messages_all.with_user(self.user_employee).read(['subject'])
        messages_all[0].with_user(self.user_employee).read(['subject'])
        messages_all[1].with_user(self.user_employee).read(['subject'])  # can read message of readonly

        with self.assertRaises(AccessError):  # fetch should be symmetric to read
            _message = messages_all[2].with_user(self.user_employee).copy_data()

        with self.assertRaises(AccessError):  # no write access at all
            messages_all.with_user(self.user_portal).read(['subject'])
        messages_all.with_user(self.user_admin).read(['subject'])

    def test_access_read_portal(self):
        """ Read access check for portal users """
        for msg, msg_vals, should_crash, reason in [
            # document based
            (self.record_portal.message_ids[0], {}, False, 'Access on record'),
            (self.record_internal.message_ids[0], {}, True, 'No access on record'),
            # author
            (self.record_internal.message_ids[0], {
                'author_id': self.user_portal.partner_id.id,
            }, False, 'Author > no access on record'),
            # notified
            (self.record_admin.message_ids[0], {
                'notification_ids': [(0, 0, {
                    'res_partner_id': self.user_portal.partner_id.id,
                })],
            }, False, 'Notified > no access on record'),
            # forbidden
            (self.record_portal.message_ids[0], {
                'subtype_id': self.env.ref('mail.mt_note').id,
            }, True, 'Note (comment) cannot be read by portal users'),
            (self.record_portal.message_ids[0], {
                'subtype_id': self.test_subtype_access_internal.id,
            }, True, 'Internal subtype (comment) cannot be read by portal users'),
            (self.record_portal.message_ids[0], {
                'message_type': 'email_outgoing',
                'subtype_id': self.env.ref('mail.mt_note').id,
            }, False, 'Note (email_outgoing) can be read by portal users'),
            (self.record_portal.message_ids[0], {
                'is_internal': True,
            }, True, 'Internal message (comment) cannot be read by portal users'),
            (self.record_portal.message_ids[0], {
                'is_internal': True,
                'message_type': 'notification',
            }, False, 'Internal message (notification) can be read by portal users'),
            (self.record_portal.message_ids[0], {
                'message_type': 'user_notification',
            }, True, 'User notifications for other people can never be read by portal users'),
        ]:
            original_vals = {
                'author_id': msg.author_id.id,
                'is_internal': False,
                'message_type': msg.message_type,
                'notification_ids': [(6, 0, {})],
                'parent_id': msg.parent_id.id,
                'subtype_id': self.env.ref('mail.mt_comment').id,
            }
            with self.subTest(msg=msg, reason=reason):
                if msg_vals:
                    msg.write(msg_vals)

                self.env.invalidate_all()
                if should_crash:
                    with self.assertRaises(AccessError):
                        msg.with_user(self.user_portal).read(['body'])
                else:
                    msg.with_user(self.user_portal).read(['body'])
                if msg_vals:
                    msg.write(original_vals)
                    self.env.invalidate_all()

    def test_access_read_public(self):
        """ Read access check for public users """
        for msg, msg_vals, should_crash, reason in [
            # document based
            (self.record_public.message_ids[0], {}, False, 'Access on record'),
            (self.record_portal.message_ids[0], {}, True, 'No access on record'),
            # author
            (self.record_internal.message_ids[0], {
                'author_id': self.user_public.partner_id.id,
            }, False, 'Author > no access on record'),
            # notified
            (self.record_admin.message_ids[0], {
                'notification_ids': [(0, 0, {
                    'res_partner_id': self.user_public.partner_id.id,
                })],
            }, False, 'Notified > no access on record'),
            # forbidden
            (self.record_public.message_ids[0], {
                'subtype_id': self.env.ref('mail.mt_note').id,
            }, True, 'Note cannot be read by public users'),
            (self.record_public.message_ids[0], {
                'is_internal': True,
            }, True, 'Internal message cannot be read by public users'),
        ]:
            original_vals = {
                'author_id': msg.author_id.id,
                'is_internal': False,
                'message_type': msg.message_type,
                'notification_ids': [(6, 0, {})],
                'parent_id': msg.parent_id.id,
                'subtype_id': self.env.ref('mail.mt_comment').id,
            }
            with self.subTest(msg=msg, reason=reason):
                if msg_vals:
                    msg.write(msg_vals)

                self.env.invalidate_all()
                if should_crash:
                    with self.assertRaises(AccessError):
                        msg.with_user(self.user_public).read(['body'])
                else:
                    msg.with_user(self.user_public).read(['body'])
                if msg_vals:
                    msg.write(original_vals)
                    self.env.invalidate_all()

    # ------------------------------------------------------------
    # UNLINK
    # - Criterion: document-based (write or create), using '_get_mail_message_access'
    # ------------------------------------------------------------

    def test_access_unlink(self):
        """ Unlink access check for internal users """
        for msg, msg_vals, should_crash, reason in [
            # document based
            (self.record_portal.message_ids[0], {}, False, 'W Access on record'),
            (self.record_internal_ro.message_ids[0], {}, True, 'R Access on record'),
            # notified
            (self.record_admin.message_ids[0], {
                'notification_ids': [(0, 0, {
                    'res_partner_id': self.user_portal.partner_id.id,
                })],
            }, True, 'Even notified, cannot remove'),
        ]:
            with self.subTest(msg=msg, reason=reason):
                if msg_vals:
                    msg.write(msg_vals)
                if should_crash:
                    with self.assertRaises(AccessError):
                        msg.with_user(self.user_portal).unlink()
                else:
                    msg.with_user(self.user_portal).unlink()

    def test_access_unlink_portal(self):
        """ Unlink access check for portal users. """
        for msg, msg_vals, should_crash, reason in [
            # document based
            (self.record_portal.message_ids[0], {}, False, 'W Access on record but unlink limited'),
            (self.record_portal_ro.message_ids[0], {}, True, 'R Access on record'),
            # notified
            (self.record_admin.message_ids[0], {
                'notification_ids': [(0, 0, {
                    'res_partner_id': self.user_portal.partner_id.id,
                })],
            }, True, 'Even notified, cannot remove'),
        ]:
            with self.subTest(msg=msg, reason=reason):
                if msg_vals:
                    msg.write(msg_vals)
                if should_crash:
                    with self.assertRaises(AccessError):
                        msg.with_user(self.user_portal).unlink()
                else:
                    msg.with_user(self.user_portal).unlink()

    # ------------------------------------------------------------
    # WRITE
    # - Criterions
    #   - author
    #   - recipients / notified
    #   - document-based (write or create), using '_get_mail_message_access'
    # ------------------------------------------------------------

    def test_access_write(self):
        """ Test updating message content as internal user """
        for msg, msg_vals, should_crash, reason in [
            # document based
            (self.record_internal.message_ids[0], {}, False, 'W Access on record'),
            (self.record_internal_ro.message_ids[0], {}, True, 'No W Access on record'),
            (self.record_admin.message_ids[0], {}, True, 'No access on record'),
            # author
            (self.record_admin.message_ids[0], {
                'author_id': self.user_employee.partner_id.id,
            }, False, 'Author > no access on record'),
            # notified
            (self.record_admin.message_ids[0], {
                'notification_ids': [(0, 0, {
                    'res_partner_id': self.user_employee.partner_id.id,
                })],
            }, False, 'Notified > no access on record'),
        ]:
            original_vals = {
                'author_id': msg.author_id.id,
                'notification_ids': [(6, 0, {})],
                'parent_id': msg.parent_id.id,
            }
            with self.subTest(msg=msg, reason=reason):
                if msg_vals:
                    msg.write(msg_vals)
                if should_crash:
                    with self.assertRaises(AccessError):
                        msg.with_user(self.user_employee).write({'body': 'Update'})
                else:
                    msg.with_user(self.user_employee).write({'body': 'Update'})
                if msg_vals:
                    msg.write(original_vals)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_write_envelope(self):
        """ Test updating message envelope require some privileges """
        message = self.record_internal.with_user(self.user_employee).message_ids[0]
        message.write({'body': 'Update Me'})
        with self.assertRaises(AccessError):
            message.write({'model': 'res.partner'})
        # To change in 18+
        message.write({'partner_ids': [(4, self.user_portal_2.partner_id.id)]})
        with self.assertRaises(AccessError):
            message.write({'res_id': self.record_public.id})
        # To change in 18+
        message.write({'notification_ids': [
            (0, 0, {'res_partner_id': self.user_portal_2.partner_id.id})
        ]})

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_write_portal_notification(self):
        """ Test updating message notification content as portal user """
        self.record_followers.message_subscribe(self.user_portal.partner_id.ids)
        test_record = self.record_followers.with_user(self.user_portal)
        test_record.read(['name'])
        with self.assertRaises(AccessError):
            test_record.with_user(self.user_portal_2).read(['name'])
        message = test_record.message_ids[0].with_user(self.user_portal)
        message.write({'body': 'Updated'})
        with self.assertRaises(AccessError):
            message.with_user(self.user_portal_2).read(['subject'])

    # ------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------

    def test_search(self):
        """ Test custom 'search' implemented on 'mail.message' that replicates
        custom rules defined on 'read' override """
        base_msg_vals = {
            'message_type': 'comment',
            'model': self.record_internal._name,
            'res_id': self.record_internal.id,
            'subject': '_ZTest',
        }

        msgs = self.env['mail.message'].create([
            dict(base_msg_vals,
                 body='Private Comment (mention portal)',
                 model=False,
                 partner_ids=[(4, self.user_portal.partner_id.id)],
                 res_id=False,
                 subtype_id=self.ref('mail.mt_comment'),
                ),
            dict(base_msg_vals,
                 body='Internal Log',
                 subtype_id=False,
                ),
            dict(base_msg_vals,
                 body='Internal Note',
                 subtype_id=self.ref('mail.mt_note'),
                ),
            dict(base_msg_vals,
                 body='Internal Comment (mention portal)',
                 partner_ids=[(4, self.user_portal.partner_id.id)],
                 subtype_id=self.ref('mail.mt_comment'),
                ),
            dict(base_msg_vals,
                 body='Internal Comment (mention employee)',
                 partner_ids=[(4, self.user_employee.partner_id.id)],
                 subtype_id=self.ref('mail.mt_comment'),
                ),
            dict(base_msg_vals,
                 body='Internal Comment',
                 subtype_id=self.ref('mail.mt_comment'),
                ),
        ])
        msg_record_admin = self.env['mail.message'].create(dict(base_msg_vals,
            body='Admin Comment',
            model=self.record_admin._name,
            res_id=self.record_admin.id,
            subtype_id=self.ref('mail.mt_comment'),
        ))
        msg_record_portal = self.env['mail.message'].create(dict(base_msg_vals,
            body='Portal Comment',
            model=self.record_portal._name,
            res_id=self.record_portal.id,
            subtype_id=self.ref('mail.mt_comment'),
        ))
        msg_record_portal_internal = self.env['mail.message'].create(dict(base_msg_vals,
            body='Internal Comment on Portal',
            is_internal=True,
            model=self.record_portal._name,
            res_id=self.record_portal.id,
            subtype_id=self.ref('mail.mt_comment'),
        ))
        msg_record_public = self.env['mail.message'].create(dict(base_msg_vals,
            body='Public Comment',
            model=self.record_public._name,
            res_id=self.record_public.id,
            subtype_id=self.ref('mail.mt_comment'),
        ))
        msg_record_public_internal = self.env['mail.message'].create(dict(base_msg_vals,
            body='Internal Comment on Public',
            is_internal=True,
            model=self.record_public._name,
            res_id=self.record_public.id,
            subtype_id=self.ref('mail.mt_comment'),
        ))

        for (test_user, add_domain), exp_messages in zip([
            (self.user_public, []),
            (self.user_portal, []),
            (self.user_employee, []),
            (self.user_employee, [('body', 'ilike', 'Internal')]),
            (self.user_admin, []),
        ], [
            # public: record with access
            msg_record_public,
            # portal: mentionned + record with access, if published
            msgs[0] + msgs[3] + msg_record_portal + msg_record_public,
            # employee
            msgs[1:6] + msg_record_portal + msg_record_portal_internal + msg_record_public + msg_record_public_internal,
            msgs[1:6] + msg_record_portal_internal + msg_record_public_internal,
            msgs[1:] + msg_record_admin + msg_record_portal + msg_record_portal_internal + msg_record_public + msg_record_public_internal,
        ]):
            with self.subTest(test_user=test_user.name, add_domain=add_domain):
                self.env.invalidate_all()
                domain = [('subject', 'like', '_ZTest')] + add_domain
                self.assertEqual(self.env['mail.message'].with_user(test_user).search(domain), exp_messages)

    def test_search_customized(self):
        """ Test '_get_mail_message_access' support in search """
        records = self.env['mail.test.access.custo'].with_user(self.user_admin).create([
            {'name': 'Open'},
            {'name': 'Open RO', 'is_readonly': True},  # internal can read thus search
            {'name': 'Soonish Locked'},
        ])
        messages_all = self.env['mail.message'].sudo()
        for user in self.user_employee + self.user_portal:
            for record in records:
                new = record.message_post(
                    body=f'AnchorForSearch / A message from {user.name}',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )
                messages_all += new.sudo()

        found_emp = self.env['mail.message'].with_user(self.user_employee).search([
            ('body', 'ilike', 'AnchorForSearch')
        ])
        self.assertEqual(found_emp, messages_all)
        found_por = self.env['mail.message'].with_user(self.user_portal).search([
            ('body', 'ilike', 'AnchorForSearch')
        ])
        self.assertEqual(found_por, messages_all)

        # lock -> locked records need 'write' access, as defined in '_get_mail_message_access'
        # hence messages are out of search, symmetrical to reading therm
        records[2].write({'is_locked': True, 'name': 'Locked !'})
        records[2].flush_recordset()
        found_emp = self.env['mail.message'].with_user(self.user_employee).search([
            ('body', 'ilike', 'AnchorForSearch')
        ])
        self.assertEqual(found_emp, messages_all.filtered(lambda m: m.res_id != records[2].id), 'Should filter like read')
        found_emp.read(['subject'])
        found_por = self.env['mail.message'].with_user(self.user_portal).search([
            ('body', 'ilike', 'AnchorForSearch')
        ])
        self.assertEqual(found_por, messages_all.filtered(lambda m: m.res_id != records[2].id), 'Should filter like read')
        found_por.read(['subject'])


@tagged('mail_message', 'security', 'post_install', '-at_install')
class TestMessageSubModelAccess(MessageAccessCommon):

    def test_ir_attachment_read_message_notification(self):
        message = self.record_admin.message_ids[0]
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt',
            'res_model': message._name,
            'res_id': message.id})
        # attach the attachment to the message
        message.write({'attachment_ids': [(4, attachment.id)]})
        message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        message.with_user(self.user_employee).read()
        # Test: Employee has access to attachment, ok because they can read message
        attachment.with_user(self.user_employee).read(['name', 'datas'])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_mail_follower(self):
        """ Read access check on sub entities of mail.message """
        internal_record = self.record_internal.with_user(self.user_employee)
        internal_record.message_subscribe(
            partner_ids=self.user_portal.partner_id.ids
        )

        # employee can access
        follower = internal_record.message_follower_ids.filtered(
            lambda f: f.partner_id == self.user_portal.partner_id
        )
        self.assertTrue(follower)
        with self.assertRaises(AccessError):
            follower.with_user(self.user_portal).read(['partner_id'])

        # employee cannot update
        with self.assertRaises(AccessError):
            follower.write({'partner_id': self.user_admin.partner_id.id})
        follower.with_user(self.user_admin).write({'partner_id': self.user_admin.partner_id.id})

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_mail_notification(self):
        """ Limit update of notifications for internal users """
        internal_record = self.record_internal.with_user(self.user_admin)
        message = internal_record.message_post(
            body='Hello People',
            message_type='comment',
            partner_ids=(self.user_portal.partner_id + self.user_employee.partner_id).ids,
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        notifications = message.with_user(self.user_employee).notification_ids
        self.assertEqual(len(notifications), 2)
        self.assertTrue(bool(notifications.read(['is_read'])), 'Internal can read')

        notif_other = notifications.filtered(lambda n: n.res_partner_id == self.user_portal.partner_id)
        with self.assertRaises(AccessError):
            notif_other.write({'is_read': True})

        notif_own = notifications.filtered(lambda n: n.res_partner_id == self.user_employee.partner_id)
        notif_own.write({'is_read': True})
        # with self.assertRaises(AccessError):
        #     notif_own.write({'author_id': self.user_portal.partner_id.id})
        with self.assertRaises(AccessError):
            notif_own.write({'mail_message_id': self.record_internal.message_ids[0]})
        with self.assertRaises(AccessError):
            notif_own.write({'res_partner_id': self.user_admin.partner_id.id})

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_mail_notification_portal(self):
        """ In any case, portal should not modify notifications """
        with self.assertRaises(AccessError):
            self.assertFalse(self.env['mail.notification'].with_user(self.user_portal).check_access('write'))
        portal_record = self.record_portal.with_user(self.user_portal)
        message = portal_record.message_post(
            body='Hello People',
            message_type='comment',
            partner_ids=(self.user_portal_2.partner_id + self.user_employee.partner_id).ids,
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        notifications = message.notification_ids
        self.assertEqual(len(notifications), 2)
        self.assertTrue(bool(notifications.read(['is_read'])), 'Portal can read')
        self.assertEqual(notifications.res_partner_id, self.user_portal_2.partner_id + self.user_employee.partner_id)
