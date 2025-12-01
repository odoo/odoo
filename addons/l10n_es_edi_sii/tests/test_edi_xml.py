# coding: utf-8
from .common import TestEsEdiCommon

import json

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('USD')

        cls.certificate.write({
            'date_start': '2019-01-01 01:00:00',
            'date_end': '2021-01-01 01:00:00',
        })

    def _send_sii_and_get_json(self, invoice):
        invoice.action_post()
        invoice.action_l10n_es_send_sii()
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('mimetype', '=', 'application/json'),
            ('res_field', '=', 'l10n_es_edi_sii_json_file'),
        ], limit=1)
        self.assertTrue(attachment, "SII JSON attachment was not created")
        return json.loads(attachment.raw)[0]

    def _mock_sii_webservice(self, invoice, info_list, cancel=False):
        return {'success': True}

    def test_010_out_invoice_s_iva10b_s_iva21s(self):
        """ Invoice with goods and services as they need to be reported in different sections for customer invoices. """
        invoice = self._create_invoice_es(
            partner_id=self.partner_b.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ns').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'PeriodoLiquidacion': {
                'Ejercicio': '2019',
                'Periodo': '01',
            },
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'INV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'FacturaExpedida': {
                'TipoFactura': 'F1',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'Contraparte': {
                    'NIF': 'F35999705',
                    'NombreRazon': 'partner_b',
                },
                'TipoDesglose': {
                    'DesgloseFactura': {
                        'Sujeta': {
                            'NoExenta': {
                                'TipoNoExenta': 'S1',
                                'DesgloseIVA': {
                                    'DetalleIVA': [{
                                        'TipoImpositivo': 10.0,
                                        'BaseImponible': 100.0,
                                        'CuotaRepercutida': 10.0,
                                    }],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': 110.0,
            },
        })

    def test_020_out_invoice_s_iva10b_s_iva0_ns(self):
        """ The ns tax is a special case with l10n_es_type ignore and should not appear in what we send"""
        invoice = self._create_invoice_es(
            partner_id=self.partner_b.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ns').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'INV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'F1',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseFactura': {
                        'Sujeta': {
                            'NoExenta': {
                                'TipoNoExenta': 'S1',
                                'DesgloseIVA': {
                                    'DetalleIVA': [
                                        {
                                            'TipoImpositivo': 10.0,
                                            'BaseImponible': 100.0,
                                            'CuotaRepercutida': 10.0
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': 110.0,
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
            },
        })

    def test_030_out_invoice_s_iva10b_s_req014_s_iva21s_s_req52(self):
        """Recargo de Equivalencia with 2 different taxes and 2 different IVAs as it is reported in the same tag as the IVA"""
        invoice = self._create_invoice_es(
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [Command.set((self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_req014')).ids)],
                },
                {
                    'price_unit': 50.0,
                    'tax_ids': [Command.set((self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_req014')).ids)],
                },
                {
                    'price_unit': 200.0,
                    'tax_ids': [Command.set((self._get_tax_by_xml_id('s_iva21s') + self._get_tax_by_xml_id('s_req52')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'INV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'F1',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'Sujeta': {
                                'NoExenta': {
                                    'TipoNoExenta': 'S1',
                                    'DesgloseIVA': {
                                        'DetalleIVA': [
                                            {
                                                'TipoImpositivo': 21.0,
                                                'BaseImponible': 200.0,
                                                'CuotaRepercutida': 42.0,
                                                'CuotaRecargoEquivalencia': 10.4,
                                                'TipoRecargoEquivalencia': 5.2
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        'Entrega': {
                            'Sujeta': {
                                'NoExenta': {
                                    'TipoNoExenta': 'S1',
                                    'DesgloseIVA': {
                                        'DetalleIVA': [
                                            {
                                                'TipoImpositivo': 10.0,
                                                'BaseImponible': 150.0,
                                                'CuotaRepercutida': 15.0,
                                                'CuotaRecargoEquivalencia': 2.1,
                                                'TipoRecargoEquivalencia': 1.4
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                },
                'ImporteTotal': 419.5,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_040_out_refund_s_iva10b_s_iva10b_s_iva21s(self):
        """For a customer refund, the amounts need to be reported as negative and also have goods and services separate"""
        invoice = self._create_invoice_es(
            move_type='out_refund',
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21s').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'RINV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'R1',
                'TipoRectificativa': 'I',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'Sujeta': {
                                'NoExenta': {
                                    'TipoNoExenta': 'S1',
                                    'DesgloseIVA': {
                                        'DetalleIVA': [
                                            {
                                                'TipoImpositivo': 21.0,
                                                'BaseImponible': -200.0,
                                                'CuotaRepercutida': -42.0
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        'Entrega': {
                            'Sujeta': {
                                'NoExenta': {
                                    'TipoNoExenta': 'S1',
                                    'DesgloseIVA': {
                                        'DetalleIVA': [
                                            {
                                                'TipoImpositivo': 10.0,
                                                'BaseImponible': -200.0,
                                                'CuotaRepercutida': -20.0
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                },
                'ImporteTotal': -462.0,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_050_out_invoice_s_iva0_sp_i_s_iva0_g_i(self):
        """An intra-community sale needs to be reported as exempt and intra-community services as no sujeto por reglas de localizacion (no_sujeto_loc)"""
        invoice = self._create_invoice_es(
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'INV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'F1',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'NoSujeta': {
                                'ImporteTAIReglasLocalizacion': 100.0
                            },
                        },
                        'Entrega': {
                            'Sujeta': {
                                'Exenta': {
                                    'DetalleExenta': [
                                        {
                                            'BaseImponible': 200.0,
                                            'CausaExencion': 'E5',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': 300.0,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_060_out_refund_s_iva0_sp_i_s_iva0_g_i(self):
        """ Intra-community refund of service and good"""
        invoice = self._create_invoice_es(
            move_type='out_refund',
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'RINV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
            'TipoFactura': 'R1',
            'TipoRectificativa': 'I',
            'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'NoSujeta': {
                                'ImporteTAIReglasLocalizacion': -100.0
                            },
                        },
                        'Entrega': {
                            'Sujeta': {
                                'Exenta': {
                                    'DetalleExenta': [
                                        {
                                            'BaseImponible': -200.0,
                                            'CausaExencion': 'E5',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': -300.0,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_070_out_invoice_s_iva_e_s_iva0_g_e(self):
        """ Export of service (no sujeto por reglas de localization) and export of goods (exempt)"""
        invoice = self._create_invoice_es(
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva_e').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_e').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'INV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'F1',
                'ClaveRegimenEspecialOTrascendencia': '02',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'NoSujeta': {
                                'ImporteTAIReglasLocalizacion': 100.0,
                            },
                        },
                        'Entrega': {
                            'Sujeta': {
                                'Exenta': {
                                    'DetalleExenta': [
                                        {
                                            'BaseImponible': 200.0,
                                            'CausaExencion': 'E2',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': 300.0,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_080_out_refund_s_iva0_sp_i_s_iva0_g_i(self):
        """Customer refund of an intracom good and service"""
        invoice = self._create_invoice_es(
            move_type='out_refund',
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'RINV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'R1',
                'TipoRectificativa': 'I',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'NoSujeta': {
                                'ImporteTAIReglasLocalizacion': -100.0,
                            },
                        },
                        'Entrega': {
                            'Sujeta': {
                                'Exenta': {
                                    'DetalleExenta': [
                                        {
                                            'BaseImponible': -200.0,
                                            'CausaExencion': 'E5',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': -300.0,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_085_out_refund_s_iva0_sp_i_s_iva0_g_i_multi_currency(self):
        """ Same as test_080 but in multi-currency"""
        invoice = self._create_invoice_es(
            move_type='out_refund',
            partner_id=self.partner_a.id,
            currency_id=self.other_currency.id,
            invoice_line_ids=[
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                {'price_unit': 400.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'RINV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'R1',
                'TipoRectificativa': 'I',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseTipoOperacion': {
                        'PrestacionServicios': {
                            'NoSujeta': {
                                'ImporteTAIReglasLocalizacion': -100.0,
                            },
                        },
                        'Entrega': {
                            'Sujeta': {
                                'Exenta': {
                                    'DetalleExenta': [
                                        {
                                            'BaseImponible': -200.0,
                                            'CausaExencion': 'E5',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': -300.0,
                'Contraparte': {
                    'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                    'NombreRazon': 'partner_a',
                },
            },
        })

    def test_090_in_invoice_p_iva10_bc_p_irpf19_p_iva21_sc_p_irpf19(self):
        """ Vendor bill 10% IVA 19% retention, 21% IVA 19% retention
        The retention just needs to be ignored basically, but in the ImporteTotal,
        we need the amount before retention (withholding). """
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf19')).ids)],
                },
                {
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva21_sc') + self._get_tax_by_xml_id('p_irpf19')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'}
            },
            'FacturaRecibida': {
                'TipoFactura': 'F1',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': 352.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {'BaseImponible': 100.0, 'CuotaSoportada': 10.0, 'TipoImpositivo': 10.0},
                            {'BaseImponible': 200.0, 'CuotaSoportada': 42.0, 'TipoImpositivo': 21.0}
                        ]
                    }
                },
                'CuotaDeducible': 52.0
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'}
        })

    def test_100_in_refund_p_iva10_bc(self):
        """Vendor bill refund of VAT 10% goods"""
        invoice = self._create_invoice_es(
            move_type='in_refund',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva10_bc').ids)]}],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'R4',
                'TipoRectificativa': 'I',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': -110.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {'BaseImponible': -100.0, 'CuotaSoportada': -10.0, 'TipoImpositivo': 10.0},
                        ],
                    },
                },
                'CuotaDeducible': -10.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_110_in_invoice_p_iva10_bc_p_req014_p_iva21_sc_p_req52(self):
        """Vendor bill with recargo de equivalencia that needs to be reported within the VAT tax"""
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_req014')).ids)],
                },
                {
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva21_sc') + self._get_tax_by_xml_id('p_req52')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'F1',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': 363.8,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {
                                'BaseImponible': 100.0,
                                'CuotaSoportada': 10.0,
                                'TipoImpositivo': 10.0,
                                'CuotaRecargoEquivalencia': 1.4,
                                'TipoRecargoEquivalencia': 1.4,
                            },
                            {
                                'BaseImponible': 200.0,
                                'CuotaSoportada': 42.0,
                                'TipoImpositivo': 21.0,
                                'CuotaRecargoEquivalencia': 10.4,
                                'TipoRecargoEquivalencia': 5.2,
                            },
                        ],
                    },
                },
                'CuotaDeducible': 52.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_120_in_invoice_p_iva21_sp_ex(self):
        """ Extra-community vendor bill with reverse charge (-100 line which changes importetotal)"""
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_ex').ids)]}],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'F1',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': 100.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'InversionSujetoPasivo': {
                        'DetalleIVA': [{
                            'BaseImponible': 100.0,
                            'CuotaSoportada': 21.0,
                            'TipoImpositivo': 21.0,
                        }],
                    },
                },
                'CuotaDeducible': 21.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_130_in_invoice_p_iva0_ns_p_iva10_bc(self):
        """Vendor bill with a line of no sujeto services and a line of 10% goods.  Here, there is no separation between goods and services"""
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva0_ns').ids)]},
                {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva10_bc').ids)]},
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'F1',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': 320.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {'BaseImponible': 100.0},
                            {'BaseImponible': 200.0, 'TipoImpositivo': 10.0, 'CuotaSoportada': 20.0},
                        ],
                    },
                },
                'CuotaDeducible': 20.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_140_out_invoice_s_iva10b_s_irpf1(self):
        """Customer invoice with a 10% VAT and a retention.  The retention should not be deducted from the importetotal."""
        invoice = self._create_invoice_es(
            partner_id=self.partner_b.id,
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_irpf1')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'IDEmisorFactura': {'NIF': '59962470K'},
                'NumSerieFacturaEmisor': 'INV/2019/00001',
                'FechaExpedicionFacturaEmisor': '01-01-2019',
            },
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'FacturaExpedida': {
                'TipoFactura': 'F1',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'DescripcionOperacion': 'manual',
                'TipoDesglose': {
                    'DesgloseFactura': {
                        'Sujeta': {
                            'NoExenta': {
                                'TipoNoExenta': 'S1',
                                'DesgloseIVA': {
                                    'DetalleIVA': [
                                        {
                                            'TipoImpositivo': 10.0,
                                            'BaseImponible': 100.0,
                                            'CuotaRepercutida': 10.0,
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
                'ImporteTotal': 110.0,
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
            },
        })

    def test_150_in_invoice_p_iva10_bc_p_irpf1(self):
        """Same as test_140 but for vendor bills"""
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'F1',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': 110.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {
                                'BaseImponible': 100.0,
                                'CuotaSoportada': 10.0,
                                'TipoImpositivo': 10.0,
                            },
                        ],
                    },
                },
                'CuotaDeducible': 10.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_160_in_refund_p_iva10_bc_p_irpf1(self):
        """Same as 150 but for supplier refunds.  The amounts need to be negative. """
        invoice = self._create_invoice_es(
            move_type='in_refund',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'R4',
                'TipoRectificativa': 'I',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': -110.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {
                                'BaseImponible': -100.0,
                                'CuotaSoportada': -10.0,
                                'TipoImpositivo': 10.0,
                            },
                        ],
                    },
                },
                'CuotaDeducible': -10.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_165_in_refund_p_iva10_bc_p_irpf1_multi_currency(self):
        """Same as test_160, but with another currency.  With double the amounts, the result is the same. """
        invoice = self._create_invoice_es(
            move_type='in_refund',
            ref='sup0001',
            partner_id=self.partner_b.id,
            currency_id=self.other_currency.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'NIF': 'F35999705', 'NombreRazon': 'partner_b'},
            },
            'FacturaRecibida': {
                'TipoFactura': 'R4',
                'TipoRectificativa': 'I',
                'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'ImporteTotal': -110.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {
                                'BaseImponible': -100.0,
                                'CuotaSoportada': -10.0,
                                'TipoImpositivo': 10.0,
                            },
                        ],
                    },
                },
                'CuotaDeducible': -10.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })

    def test_170_in_invoice_dua(self):
        """DUA invoice.  The TipoFactura needs to change as well as the importetotal needs to include the base. """
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='fakedua',
            partner_id=self.partner_b.id,
            currency_id=self.other_currency.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva21_ibc_group').ids))],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'PeriodoLiquidacion': {'Ejercicio': '2019', 'Periodo': '01'},
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'IDEmisorFactura': {'NIF': '59962470K',
                                    'NombreRazon': 'partner_b'},
                'NumSerieFacturaEmisor': 'fakedua'
            },
            'FacturaRecibida': {
                'DescripcionOperacion': 'manual',
                'Contraparte': {'NIF': '59962470K', 'NombreRazon': 'partner_b'},
                'FechaRegContable': '02-01-2019',
                'ClaveRegimenEspecialOTrascendencia': '01',
                'TipoFactura': 'F5',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [{'BaseImponible': 500.0, 'TipoImpositivo': 21.0, 'CuotaSoportada': 105.0}]
                    }
                },
                'ImporteTotal': 605.0,
                'CuotaDeducible': 105.0
            }
        })

    def test_180_in_invoice_iva21_sp_in_iva21_ic_bc(self):
        """ For intra-community purchase of services and goods, the -100 needs to be taken into account in the importe total.
        The clave should also change to 09. """
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_a.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_in').ids)],
                },
                {
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_ic_bc').ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'IDOtro': {'IDType': '02', 'ID': 'BE0477472701'}, 'NombreRazon': 'partner_a'}
            },
            'FacturaRecibida': {
                'TipoFactura': 'F1',
                'Contraparte': {'IDOtro': {'IDType': '02', 'ID': 'BE0477472701'}, 'NombreRazon': 'partner_a'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '09',
                'ImporteTotal': 300.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {'BaseImponible': 300.0, 'CuotaSoportada': 63.0, 'TipoImpositivo': 21.0},
                        ]
                    }
                },
                'CuotaDeducible': 63.0
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'}
        })

    def test_190_in_refund_iva21_sp_in_iva21_ic_bc(self):
        """ For intra-community purchase return services and goods, the -100 needs to be taken into account in the importe total.
        For a refund, the type should change to R4"""
        invoice = self._create_invoice_es(
            move_type='in_refund',
            ref='sup0001',
            partner_id=self.partner_a.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_in').ids)],
                },
                {
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_ic_bc').ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {'IDOtro': {'IDType': '02', 'ID': 'BE0477472701'}, 'NombreRazon': 'partner_a'}
            },
            'FacturaRecibida': {
                'TipoFactura': 'R4',
                'TipoRectificativa': 'I',
                'Contraparte': {'IDOtro': {'IDType': '02', 'ID': 'BE0477472701'}, 'NombreRazon': 'partner_a'},
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '09',
                'ImporteTotal': -300.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {'BaseImponible': -300.0, 'CuotaSoportada': -63.0, 'TipoImpositivo': 21.0},
                        ]
                    }
                },
                'CuotaDeducible': -63.0
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'}
        })

    def test_200_in_invoice_p_iva12_agr(self):
        """ For bills with the 12% agricuture tax the Clave Regime Special should be E2
        """
        invoice = self._create_invoice_es(
            move_type='in_invoice',
            ref='sup0001',
            partner_id=self.partner_b.id,
            l10n_es_registration_date='2019-01-02',
            invoice_line_ids=[
                {
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva12_agr').ids)],
                },
            ],
        )
        with patch(
            'odoo.addons.l10n_es_edi_sii.models.account_move.AccountMove._l10n_es_edi_call_web_service_sign',
            autospec=True,
            side_effect=self._mock_sii_webservice,
        ):
            json_file = self._send_sii_and_get_json(invoice)
        self.assertEqual(json_file, {
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': '01-01-2019',
                'NumSerieFacturaEmisor': 'sup0001',
                'IDEmisorFactura': {
                    'NIF': 'F35999705',
                    'NombreRazon': 'partner_b',
                },
            },
            'FacturaRecibida': {
                'TipoFactura': 'F6',
                'Contraparte': {
                    'NIF': 'F35999705',
                    'NombreRazon': 'partner_b',
                },
                'DescripcionOperacion': 'manual',
                'ClaveRegimenEspecialOTrascendencia': '02',
                'ImporteTotal': 224.0,
                'FechaRegContable': '02-01-2019',
                'DesgloseFactura': {
                    'DesgloseIVA': {
                        'DetalleIVA': [
                            {
                                'BaseImponible': 200.0,
                                'ImporteCompensacionREAGYP': 24.0,
                                'PorcentCompensacionREAGYP': 12.0,
                            },
                        ],
                    },
                },
                'CuotaDeducible': 0.0,
            },
            'PeriodoLiquidacion': {'Periodo': '01', 'Ejercicio': '2019'},
        })
