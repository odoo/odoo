from odoo.tests import tagged
from .common import TestL10nEsEdiVerifactuCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiVerifactuMisc(TestL10nEsEdiVerifactuCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_huella_generation(self):
        render_values = {
            "RegistroAlta": {
                "IDFactura": {
                    "IDEmisorFactura": "  89890001K  ",
                    "NumSerieFactura": "  12345678/G33  ",
                    "FechaExpedicionFactura": "  01-01-2024  ",
                },
                "TipoFactura": "  F1  ",
                "CuotaTotal": "  12.35  ",
                "ImporteTotal": "  123.45  ",
                "Encadenamiento": {},  # no previous record
                "FechaHoraHusoGenRegistro": "  2024-01-01T19:20:30+01:00  ",
            }
        }
        fingerprint = self.env['l10n_es_edi_verifactu.xml']._fingerprint(render_values)
        self.assertEqual(fingerprint, "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60")

        render_values = {
            "RegistroAlta": {
                "IDFactura": {
                    "IDEmisorFactura": "  89890001K  ",
                    "NumSerieFactura": "  12345679/G34  ",
                    "FechaExpedicionFactura": "  01-01-2024  ",
                },
                "TipoFactura": "  F1  ",
                "CuotaTotal": "  12.35  ",
                "ImporteTotal": "  123.45  ",
                "Encadenamiento": {
                    "RegistroAnterior": {
                        "Huella": "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60",
                    },
                },
                "FechaHoraHusoGenRegistro": "  2024-01-01T19:20:35+01:00  ",
            }
        }
        fingerprint = self.env['l10n_es_edi_verifactu.xml']._fingerprint(render_values)
        self.assertEqual(fingerprint, "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97")

        render_values = {
            "RegistroAnulacion": {
                "IDFactura": {
                    "IDEmisorFacturaAnulada": "  89890001K  ",
                    "NumSerieFacturaAnulada": "  12345679/G34  ",
                    "FechaExpedicionFacturaAnulada": "  01-01-2024  ",
                },
                "Encadenamiento": {
                    "RegistroAnterior": {
                        "Huella": "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97",
                    },
                },
                "FechaHoraHusoGenRegistro": "  2024-01-01T19:20:40+01:00  ",
            },
        }
        fingerprint = self.env['l10n_es_edi_verifactu.xml']._fingerprint(render_values)
        self.assertEqual(fingerprint, "177547C0D57AC74748561D054A9CEC14B4C4EA23D1BEFD6F2E69E3A388F90C68")
