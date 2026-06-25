# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPartnerName(TestPhCommon):

    def test_name_computation_corporate(self):
        partner = self.env['res.partner'].create({"name": "My Corporation", "l10n_ph_entity_type": "corporation"})

        self.assertFalse(partner.l10n_ph_first_name)
        self.assertFalse(partner.l10n_ph_middle_name)
        self.assertFalse(partner.l10n_ph_last_name)

    def test_name_computation(self):
        """ Catch all test that iterate through a list of various name formats, and assert that our logic split these correctly. """
        # Dict of names: expected splits used to test our computation logic.
        names_to_test = {
            "Jose Rizal": ("Jose", "", "Rizal"),
            "Maria Clara Santos Reyes": ("Maria Clara", "Santos", "Reyes"),
            "Jose Maria Eduardo Santos Reyes": ("Jose Maria Eduardo", "Santos", "Reyes"),
            "Rizal": ("", "", "Rizal"),
            "   Pedro   ": ("", "", "Pedro"),
            "Juan dela Cruz": ("Juan", "", "dela Cruz"),
            "Ana de la Rosa": ("Ana", "", "de la Rosa"),
            "Miguel del Rosario": ("Miguel", "", "del Rosario"),
            "Maria de los Santos": ("Maria", "", "de los Santos"),
            "Jose San Diego": ("Jose", "", "San Diego"),
            "Juan dela Cruz Reyes": ("Juan", "dela Cruz", "Reyes"),
            "Juan San Miguel Cruz": ("Juan", "San Miguel", "Cruz"),
            "Ana Sta Maria Bautista": ("Ana", "Sta Maria", "Bautista"),
            "Miguel de los Reyes Garcia": ("Miguel", "de los Reyes", "Garcia"),
            "Jose Sto Tomas Mendoza": ("Jose", "Sto Tomas", "Mendoza"),
            "Maria Anna de los Reyes dela Cruz": ("Maria Anna", "de los Reyes", "dela Cruz"),
            "Jose San Juan de Castro": ("Jose", "San Juan", "de Castro"),
            "Carlos del Mundo Sta Maria": ("Carlos", "del Mundo", "Sta Maria"),
            "Luz de la Peña del Rosario": ("Luz", "de la Peña", "del Rosario"),
            "Maria del Carmen Santos Reyes": ("Maria del Carmen", "Santos", "Reyes"),
            "Sancho Panza dela Cruz": ("Sancho", "Panza", "dela Cruz"),
            "Mac Arthur Tolentino dela Rosa": ("Mac Arthur", "Tolentino", "dela Rosa"),
            "Maria del Carmen de los Santos dela Peña": ("Maria del Carmen", "de los Santos", "dela Peña"),
            "Juan Miguel Mac Arthur de la Rosa San Jose": ("Juan Miguel Mac Arthur", "de la Rosa", "San Jose"),
            "Maria-Clara delos Santos-Reyes": ("Maria-Clara", "", "delos Santos-Reyes"),
            "Jose-Maria dela Cruz Garcia-Lopez": ("Jose-Maria", "dela Cruz", "Garcia-Lopez"),
            "  Juan   Miguel   de  la   Cruz  ": ("Juan", "Miguel", "de la Cruz"),
            "Maria   dela   Peña   Santos": ("Maria", "dela Peña", "Santos"),
            "Juan dela Cruz Jr.": ("Juan Jr", "", "dela Cruz"),
            "Fernando Poe Jr": ("Fernando Jr", "", "Poe"),
            "Emilio Aguinaldo Sr.": ("Emilio Sr", "", "Aguinaldo"),
            "Jose Maria Santos Reyes III": ("Jose Maria III", "Santos", "Reyes"),
            "Ramon Magsaysay IV": ("Ramon IV", "", "Magsaysay"),
            "Rosa Santos Vda. de Ramos": ("Rosa", "Santos", "Vda. de Ramos"),
            "Maria Cruz Vda de los Reyes": ("Maria", "Cruz", "Vda de los Reyes"),
            "Juan dela Cruz, Jr.": ("Juan Jr", "", "dela Cruz"),
            "Jose Maria Santos Reyes, III": ("Jose Maria III", "Santos", "Reyes"),
            "Atty. Juan dela Cruz": ("Juan", "", "dela Cruz"),
            "Dr. Maria Clara Santos Reyes": ("Maria Clara", "Santos", "Reyes"),
            "Engr Lito Cruz": ("Lito", "", "Cruz"),
            "Atty. Juan dela Cruz, Jr.": ("Juan Jr", "", "dela Cruz"),
        }

        partner = self.env['res.partner'].create({"name": "Test Partner"})
        for name, expected_split in names_to_test.items():
            partner.name = name

            self.assertEqual(
                partner.l10n_ph_first_name, expected_split[0],
                f"{name}'s first names failed to be parsed correctly.\n"
                f"Expected {expected_split[0]}, got: {partner.l10n_ph_first_name}",
            )
            self.assertEqual(
                partner.l10n_ph_middle_name, expected_split[1],
                f"{name}'s middle name failed to be parsed correctly.\n"
                f"Expected {expected_split[1]}, got: {partner.l10n_ph_middle_name}",
            )
            self.assertEqual(
                partner.l10n_ph_last_name, expected_split[2],
                f"{name}'s last name failed to be parsed correctly.\n"
                f"Expected {expected_split[2]}, got: {partner.l10n_ph_last_name}",
            )
