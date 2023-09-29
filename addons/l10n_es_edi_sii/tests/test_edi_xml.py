# coding: utf-8
from .common import TestEsEdiCommon

import json

from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests import tagged


def mocked_l10n_es_edi_call_web_service_sign(edi_format, invoices, info_list):
    return {inv: {'success': True} for inv in invoices}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.certificate.write({
            'date_start': '2019-01-01 01:00:00',
            'date_end': '2021-01-01 01:00:00',
        })

    def test_010_out_invoice_s_iva10b_s_iva21s(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21s').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
                                                },
                                            ],
                                        },
                                    },
                                },
                            },
                            'Entrega': {
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
                    },
                    'ImporteTotal': 352.0,
                    'Contraparte': {
                        'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                        'NombreRazon': 'partner_a',
                    },
                },
            })

    def test_020_out_invoice_s_iva10b_s_iva0_ns(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ns').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_req014')).ids)],
                    },
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('s_iva21s') + self._get_tax_by_xml_id('s_req52')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
                                                    'BaseImponible': 100.0,
                                                    'CuotaRepercutida': 10.0,
                                                    'CuotaRecargoEquivalencia': 1.4,
                                                    'TipoRecargoEquivalencia': 1.4
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    },
                    'ImporteTotal': 363.8,
                    'Contraparte': {
                        'IDOtro': {'ID': 'BE0477472701', 'IDType': '02'},
                        'NombreRazon': 'partner_a',
                    },
                },
            })

    def test_040_out_refund_s_iva10b_s_iva10b_s_iva21s(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21s').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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

    def test_050_out_invoice_s_iva0_sp_i_s_iva0_ic(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ic').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
                                    'ImportePorArticulos7_14_Otros': 100.0
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

    def test_060_out_refund_s_iva0_sp_i_s_iva0_ic(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ic').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
                                    'ImportePorArticulos7_14_Otros': -100.0
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

    def test_070_out_invoice_s_iva_e_s_iva0_e(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva_e').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_e').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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

    def test_080_out_refund_s_iva0_sp_i_s_iva0_ic(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ic').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
                                    'ImportePorArticulos7_14_Otros': -100.0,
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

    def test_085_out_refund_s_iva0_sp_i_s_iva0_ic_multi_currency(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                currency_id=self.currency_data['currency'].id,
                invoice_line_ids=[
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 400.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ic').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
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
                                    'ImportePorArticulos7_14_Otros': -100.0,
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
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
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'}
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_refund',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva10_bc').ids)]}],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
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
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_ex').ids)]}],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
                },
                'FacturaRecibida': {
                    'TipoFactura': 'F1',
                    'Contraparte': {'NombreRazon': 'partner_b', 'NIF': 'F35999705'},
                    'DescripcionOperacion': 'manual',
                    'ClaveRegimenEspecialOTrascendencia': '01',
                    'ImporteTotal': 121.0,
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
        # TODO make it work
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva0_ns').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva10_bc').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
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
        # TODO: debug
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_irpf1')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]

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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
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
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
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
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
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
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_refund',
                ref='sup0001',
                partner_id=self.partner_b.id,
                currency_id=self.currency_data['currency'].id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            json_file = json.loads(generated_files[0].decode())[0]
            self.assertEqual(json_file, {
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': '01-01-2019',
                    'NumSerieFacturaEmisor': 'sup0001',
                    'IDEmisorFactura': {'NIF': 'F35999705'},
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
