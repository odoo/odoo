from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class testSnailmailLetter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.letter = cls._create_snailmail_letter()

    @classmethod
    def _create_snailmail_letter(cls, res_id=1, model='res.partner', partner=None, **kwargs):
        partner = partner or cls.partner
        return cls.env['snailmail.letter'].create({
            'model': model,
            'res_id': res_id,
            'partner_id': partner.id,
            **kwargs
        })

    def test_snailmail_letter_invalid_model(self):
        with self.assertRaises(ValidationError):
            self._create_snailmail_letter(model='invalid.model')

        # case for valid model but doesn't support snailmail
        with self.assertRaises(ValidationError):
            self._create_snailmail_letter(model='bus.presence')

    def test_snailmail_letter_invalid_document_id(self):
        with self.assertRaises(ValidationError):
            self._create_snailmail_letter(res_id=0)

    def test_snailmail_letter_record_updation_using_invalid_write_vals(self):
        with self.assertRaises(ValidationError):
            self.letter.write({'res_id': 0})

        with self.assertRaises(ValidationError):
            self.letter.write({'model': 'res.users'})
