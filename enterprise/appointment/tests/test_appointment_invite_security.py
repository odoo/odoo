from odoo.addons.appointment.tests.common import AppointmentSecurityCommon
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'security')
class TestAppointmentInviteSecurity(AppointmentSecurityCommon):

    @users('apt_manager')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_invite_access_apt_manager(self):
        """  Test security access to appointment.invite for the group_appointment_manager.
        Can read / write / create / unlink any share link.
        """
        self._prepare_link_with_user()
        for share_link in self.all_share_link:
            with self.subTest(share_link=share_link):
                share_link.read(['resources_choice'])
                share_link.write({'resources_choice': 'current_user'})
                share_link.unlink()

        self.env['appointment.invite'].create({
            'appointment_type_ids': self.apt_type_apt_manager
        })

    @users('apt_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_invite_access_apt_user(self):
        """  Test security access to appointment.invite for the group_appointment_user.
        Can create a share link.
        Can read a share link that:
            - if it is created by him.
            - if he is present as the staff user in the share link.
        Can write a share link that is created by him only.
        Can unlink a share link that is created by him only.
        """
        self._prepare_link_with_user()
        # Can't read the share link in which he is not assigned as staff user.
        with self.assertRaises(AccessError):
            self.share_link_apt_manager.read(['resources_choice'])

        # Can create a share link.
        test_share_link = self.env['appointment.invite'].create({
            'appointment_type_ids': self.apt_type_apt_user,
        })

        # Can't write or unlink share link created by someone else.
        for share_link in self.all_share_link:
            with self.subTest(share_link=share_link), self.assertRaises(AccessError):
                share_link.write({'resources_choice': 'current_user'})
            with self.subTest(share_link=share_link), self.assertRaises(AccessError):
                share_link.unlink()

        # Can only write or unlink share link created by himself.
        test_share_link.write({'resources_choice': 'specific_resources'})
        test_share_link.unlink()

    @users('internal_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_invite_access_internal_user(self):
        """  Test security access to appointment.invite for the base.group_user.
        Can create a share link.
        Can read a share link that:
            - if it is created by him.
            - if he is present as the staff user in the share link.
        Can write a share link that it is created by him only.
        """
        self._prepare_link_with_user()
        # Can't read the share link in which he is not assigned as staff user.
        with self.assertRaises(AccessError):
            self.share_link_apt_manager.read(['resources_choice'])

        # Can create a share link.
        test_share_link = self.env['appointment.invite'].create({
            'appointment_type_ids': self.apt_type_apt_user,
        })

        # Can only write on share link created by himself.
        for share_link in self.all_share_link:
            with self.subTest(share_link=share_link), self.assertRaises(AccessError):
                share_link.write({'resources_choice': 'current_user'})
        test_share_link.write({'resources_choice': 'specific_resources'})

    def _prepare_link_with_user(self):
        """ Prepare the share Link types by applying the user to be the one from the environment. """
        self.share_link_apt_manager = self.share_link_apt_manager.with_user(self.env.user)
        self.share_link_apt_user = self.share_link_apt_user.with_user(self.env.user)
        self.share_link_internal_user = self.share_link_internal_user.with_user(self.env.user)
        self.all_share_link = self.share_link_apt_manager + self.share_link_apt_user + self.share_link_internal_user
