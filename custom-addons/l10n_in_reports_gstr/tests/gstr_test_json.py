from datetime import date
TEST_DATE = date(2023, 5, 20)
gstr1_test_json = {
  'gstin': '24AAGCC7144L6ZE',
  'fp': TEST_DATE.strftime("%m%Y"),
  'b2b': [
    {
      'ctin': '27BBBFF5679L8ZR',
      'inv': [
        {
          'inum': 'INV/2023/00010',
          'idt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 2580.0,
          'pos': '27',
          'rchrg': 'N',
          'inv_typ': 'R',
          'itms': [
            {
              'num': 1,
              'itm_det': {
                'txval': 1000.0,
                'iamt': 180.0,
                'camt': 0.0,
                'samt': 0.0,
                'csamt': 0.0,
                'rt': 18.0
              }
            }
          ],
        },
        {
          'inum': 'INV/2023/00001',
          'idt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 1180.0,
          'pos': '27',
          'rchrg': 'N',
          'inv_typ': 'R',
          'itms': [
            {
              'num': 1,
              'itm_det': {
                'txval': 1000.0,
                'iamt': 180.0,
                'camt': 0.0,
                'samt': 0.0,
                'csamt': 0.0,
                'rt': 18.0
              }
            }
          ],
        },
      ],
    },
    {
      'ctin': '24BBBFF5679L8ZR',
      'inv': [
        {
          'inum': 'INV/2023/00002',
          'idt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 1180.0,
          'pos': '24',
          'rchrg': 'N',
          'inv_typ': 'R',
          'itms': [
            {
              'num': 1,
              'itm_det': {
                'txval': 1000.0,
                'iamt': 0.0,
                'camt': 90.0,
                'samt': 90.0,
                'csamt': 0.0,
                'rt': 18.0,
              },
            }
          ],
        }
      ]
    }
  ],
  'b2cl': [
    {
      'pos': '27',
      'inv': [
        {
          'inum': 'INV/2023/00004',
          'idt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 295000.0,
          'itms': [
            {
              'num': 1,
              'itm_det': {
                'txval': 250000.0,
                'iamt': 45000.0,
                'csamt': 0.0,
                'rt': 18.0
              }
            }
          ]
        }
      ]
    }
  ],
  'b2cs': [
    {
      'sply_ty': 'INTER',
      'pos': '27',
      'typ': 'OE',
      'rt': 18.0,
      'txval': -125000.0,
      'iamt': -22500.0,
      'samt': 0.0,
      'camt': 0.0,
      'csamt': 0.0
    },
    {
      'sply_ty': 'INTRA',
      'pos': '24',
      'typ': 'OE',
      'rt': 18.0,
      'txval': 500.0,
      'iamt': 0.0,
      'samt': 45.0,
      'camt': 45.0,
      'csamt': 0.0
    }
  ],
  'cdnr': [
    {
      'ctin': '24BBBFF5679L8ZR',
      'nt': [
        {
          'ntty': 'C',
          'nt_num': 'RINV/2023/00002',
          'nt_dt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 590.0,
          'pos': '24',
          'rchrg': 'N',
          'inv_typ': 'R',
          'itms': [
            {
              'num': 1,
              'itm_det': {
                'rt': 18.0,
                'txval': 500.0,
                'iamt': 0.0,
                'samt': 45.0,
                'camt': 45.0,
                'csamt': 0.0
              }
            }
          ]
        }
      ]
    },
    {
      'ctin': '27BBBFF5679L8ZR',
      'nt': [
        {
          'ntty': 'C',
          'nt_num': 'RINV/2023/00001',
          'nt_dt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 590.0,
          'pos': '27',
          'rchrg': 'N',
          'inv_typ': 'R',
          'itms': [
            {
              'num': 1,
              'itm_det': {
                'rt': 18.0,
                'txval': 500.0,
                'iamt': 90.0,
                'samt': 0.0,
                'camt': 0.0,
                'csamt': 0.0
              }
            }
          ]
        }
      ]
    }
  ],
  'cdnur': [
    {
      'ntty': 'C',
      'nt_num': 'RINV/2023/00005',
      'nt_dt': TEST_DATE.strftime("%d-%m-%Y"),
      'val': 590.0,
      'typ': 'EXPWP',
      'itms': [
        {
          'num': 1,
          'itm_det': {
            'rt': 18.0,
            'txval': 500.0,
            'iamt': 90.0,
            'csamt': 0.0
          }
        }
      ]
    }
  ],
  'exp': [
    {
      'exp_typ': 'WPAY',
      'inv': [
        {
          'inum': 'INV/2023/00005',
          'idt': TEST_DATE.strftime("%d-%m-%Y"),
          'val': 1180.0,
          'itms': [
            {
              'rt': 18.0,
              'txval': 1000.0,
              'iamt': 180.0,
              'csamt': 0.0
            }
          ]
        }
      ]
    }
  ],
  'nil': {
    'inv': [
      {
        'sply_ty': 'INTRB2B',
        'nil_amt': 1900.0,
        'expt_amt': 500.0,
        'ngsup_amt': 500.0
      }
    ]
  },
  'hsn': {
    'data': [
      {
        'hsn_sc': '01111',
        'uqc': 'UNT',
        'rt': 0,
        'qty': 5.0,
        'txval': 2900.0,
        'iamt': 0.0,
        'samt': 0.0,
        'camt': 0.0,
        'csamt': 0.0,
        'num': 1
      },
      {
        'hsn_sc': '01111',
        'uqc': 'UNT',
        'rt': 18,
        'qty': 6.5,
        'txval': 128000.0,
        'iamt': 22860.0,
        'samt': 90.0,
        'camt': 90.0,
        'csamt': 0.0,
        'num': 2
      }
    ]
  }
}

gstr1_test_2_json = {
    "gstin": "24AAGCC7144L6ZE",
    "fp": "052023",
    "b2b": [
        {
            "ctin": "27BBBFF5679L8ZR",
            "inv": [
                {
                    "inum": "INV/2023/00003",
                    "idt": "20-05-2023",
                    "val": 1180.0,
                    "pos": "27",
                    "rchrg": "N",
                    "inv_typ": "R",
                    "itms": [
                        {
                            "num": 1,
                            "itm_det": {
                                "txval": 1000.0,
                                "iamt": 180.0,
                                "camt": 0.0,
                                "samt": 0.0,
                                "csamt": 0.0,
                                "rt": 18.0,
                            },
                        }
                    ],
                }
            ],
        },
        {
            "ctin": "27BBBFF5679L8ZR",
            "inv": [
                {
                    "inum": "INV/2023/00002",
                    "idt": "20-05-2023",
                    "val": 1180.0,
                    "pos": "27",
                    "rchrg": "N",
                    "inv_typ": "R",
                    "itms": [
                        {
                            "num": 1,
                            "itm_det": {
                                "txval": 1000.0,
                                "iamt": 180.0,
                                "camt": 0.0,
                                "samt": 0.0,
                                "csamt": 0.0,
                                "rt": 18.0,
                            },
                        }
                    ],
                }
            ],
        },
        {
            "ctin": "27BBBFF5679L8ZR",
            "inv": [
                {
                    "inum": "INV/2023/00001",
                    "idt": "20-05-2023",
                    "val": 1180.0,
                    "pos": "27",
                    "rchrg": "N",
                    "inv_typ": "DE",
                    "itms": [
                        {
                            "num": 1,
                            "itm_det": {
                                "txval": 1000.0,
                                "iamt": 180.0,
                                "camt": 0.0,
                                "samt": 0.0,
                                "csamt": 0.0,
                                "rt": 18.0,
                            },
                        }
                    ],
                }
            ],
        },
    ],
    "b2cl": [],
    "b2cs": [],
    "cdnr": [
        {
            "ctin": "27BBBFF5679L8ZR",
            "nt": [
                {
                    "ntty": "C",
                    "nt_num": "RINV/2023/00003",
                    "nt_dt": "20-05-2023",
                    "val": 590.0,
                    "pos": "27",
                    "rchrg": "N",
                    "inv_typ": "R",
                    "itms": [
                        {
                            "num": 1,
                            "itm_det": {
                                "rt": 18.0,
                                "txval": 500.0,
                                "iamt": 90.0,
                                "samt": 0.0,
                                "camt": 0.0,
                                "csamt": 0.0,
                            },
                        }
                    ],
                }
            ],
        },
        {
            "ctin": "27BBBFF5679L8ZR",
            "nt": [
                {
                    "ntty": "C",
                    "nt_num": "RINV/2023/00002",
                    "nt_dt": "20-05-2023",
                    "val": 590.0,
                    "pos": "27",
                    "rchrg": "N",
                    "inv_typ": "R",
                    "itms": [
                        {
                            "num": 1,
                            "itm_det": {
                                "rt": 18.0,
                                "txval": 500.0,
                                "iamt": 90.0,
                                "samt": 0.0,
                                "camt": 0.0,
                                "csamt": 0.0,
                            },
                        }
                    ],
                }
            ],
        },
        {
            "ctin": "27BBBFF5679L8ZR",
            "nt": [
                {
                    "ntty": "C",
                    "nt_num": "RINV/2023/00001",
                    "nt_dt": "20-05-2023",
                    "val": 590.0,
                    "pos": "27",
                    "rchrg": "N",
                    "inv_typ": "DE",
                    "itms": [
                        {
                            "num": 1,
                            "itm_det": {
                                "rt": 18.0,
                                "txval": 500.0,
                                "iamt": 90.0,
                                "samt": 0.0,
                                "camt": 0.0,
                                "csamt": 0.0,
                            },
                        }
                    ],
                }
            ],
        },
    ],
    "cdnur": [],
    "exp": [],
    "hsn": {
        "data": [
            {
                "hsn_sc": "01111",
                "uqc": "UNT",
                "rt": 18,
                "qty": 3.0,
                "txval": 1500.0,
                "iamt": 270.0,
                "samt": 0.0,
                "camt": 0.0,
                "csamt": 0.0,
                "num": 1,
            }
        ]
    },
}

gstr2b_test_json = {
  "chksum": "ADFADRGA4GADFADGERER",
  "data": {
    "data": {
      "gstin": "01AABCE2207R1Z5",
      "rtnprd": TEST_DATE.strftime("%m%Y"),
      "version": "1.0",
      "gendt": TEST_DATE.strftime("%d-%m-%Y"),
      "docdata": {
        "b2b": [
          {
            "ctin": "27BBBFF5679L8ZR",
            "trdnm": "Tiny Erp Private Limited",
            "supfildt": TEST_DATE.strftime("%d-%m-%Y"),
            "supprd": TEST_DATE.strftime("%m%Y"),
            "inv": [
              {
                "inum": "INV/001",
                "typ": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 944.0,
                "pos": "06",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 800,
                    "igst": 944,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "inum": "INV/002",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 944.0,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "inum": "INV/003",
                "typ": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 123444.16,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 11,
                    "rt": 55,
                    "txval": 4400,
                    "igst": 40,
                    "cgst": 2200,
                    "sgst": 2200,
                    "cess": 20
                  }
                ]
              },
              {
                "inum": "INV/004",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 123444.16,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 11,
                    "rt": 55,
                    "txval": 4400,
                    "igst": 40,
                    "cgst": 2200,
                    "sgst": 2200,
                    "cess": 20
                  },
                  {
                    "num": 20,
                    "rt": 24,
                    "txval": 2040,
                    "igst": 240,
                    "cgst": 200,
                    "sgst": 2040,
                    "cess": 20
                  }
                ]
              },
              {
                "inum": "CR/002",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 944.0,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 11,
                    "rt": 55,
                    "txval": 4400,
                    "igst": 40,
                    "cgst": 2200,
                    "sgst": 2200,
                    "cess": 20
                  },
                  {
                    "num": 20,
                    "rt": 18,
                    "txval": 2040,
                    "igst": 240,
                    "cgst": 200,
                    "sgst": 2040,
                    "cess": 20
                  }
                ]
              },
              {
                "inum": "CR/003",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 1180.0,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 1000,
                    "igst": 180,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "inum": "INV/013",
                "typ": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 2360.0,
                "pos": "06",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 2000,
                    "igst": 360,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
            ]
          },
          {
            "ctin": "24BBBFF5679L8ZR",
            "trdnm": "Tiny Erp Private Limited",
            "supfildt": TEST_DATE.strftime("%d-%m-%Y"),
            "supprd": TEST_DATE.strftime("%m%Y"),
            "inv": [
              {
                "inum": "INV/007",
                "typ": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 944.0,
                "pos": "06",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "inum": "INV/008",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 944.0,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "inum": "INV/009",
                "typ": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 123444.16,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 11,
                    "rt": 55,
                    "txval": 4400,
                    "igst": 40,
                    "cgst": 2200,
                    "sgst": 2200,
                    "cess": 20
                  }
                ]
              },
              {
                "inum": "INV/010",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 123444.16,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 11,
                    "rt": 55,
                    "txval": 4400,
                    "igst": 40,
                    "cgst": 2200,
                    "sgst": 2200,
                    "cess": 20
                  },
                  {
                    "num": 20,
                    "rt": 24,
                    "txval": 2040,
                    "igst": 240,
                    "cgst": 200,
                    "sgst": 2040,
                    "cess": 20
                  }
                ]
              },
              {
                "inum": "CR/004",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 944.0,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 11,
                    "rt": 18,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "inum": "CR/005",
                "typ": "R",
                "dt": "27-01-2023",
                "val": 1180.0,
                "pos": "96",
                "rev": "N",
                "itcavl": "N",
                "rsn": "P",
                "diffprcnt": 1,
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 1000,
                    "igst": 180,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              }

            ]
            }
        ],
        "cdnr": [
          {
            "ctin": "01AAAAP1208Q1ZS",
            "trdnm": "GSTN",
            "supfildt": TEST_DATE.strftime("%d-%m-%Y"),
            "supprd": TEST_DATE.strftime("%m%Y"),
            "nt": [
              {
                "ntnum": "533515",
                "typ": "C",
                "suptyp": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 729248.16,
                "pos": "01",
                "rev": "N",
                "itcavl": "N",
                "rsn": "C",
                "diffprcnt": 1,
                "srctyp": "e-Invoice",
                "irn": "897ADG56RTY78956HYUG90BNHHIJK453GFTD99845672FDHHHSHGFH4567FG56TR",
                "irngendate": TEST_DATE.strftime("%d-%m-%Y"),
                "items": [
                  {
                    "num": 1,
                    "rt": 5,
                    "txval": 400,
                    "igst": 400,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              }
            ]
          },
          {
            "ctin": "27BBBFF5679L8ZR",
            "trdnm": "Tiny Erp Private Limited",
            "supfildt": TEST_DATE.strftime("%d-%m-%Y"),
            "supprd": TEST_DATE.strftime("%m%Y"),
            "nt": [
              {
                "ntnum": "CR/001",
                "typ": "C",
                "suptyp": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 944.0,
                "pos": "01",
                "rev": "N",
                "itcavl": "N",
                "rsn": "C",
                "diffprcnt": 1,
                "srctyp": "e-Invoice",
                "irn": "897ADG56RTY78956HYUG90BNHHIJK453GFTD99845672FDHHHSHGFH4567FG56TR",
                "irngendate": "27-01-2023",
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "ntnum": "INV/005",
                "typ": "C",
                "suptyp": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 944.0,
                "pos": "01",
                "rev": "N",
                "itcavl": "N",
                "rsn": "C",
                "diffprcnt": 1,
                "srctyp": "e-Invoice",
                "irn": "897ADG56RTY78956HYUG90BNHHIJK453GFTD99845672FDHHHSHGFH4567FG56TR",
                "irngendate": "27-01-2023",
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "ntnum": "INV/006",
                "typ": "C",
                "suptyp": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 1180.0,
                "pos": "01",
                "rev": "N",
                "itcavl": "N",
                "rsn": "C",
                "diffprcnt": 1,
                "srctyp": "e-Invoice",
                "irn": "897ADG56RTY78956HYUG90BNHHIJK453GFTD99845672FDHHHSHGFH4567FG56TR",
                "irngendate": "27-01-2023",
                "items": [
                  {
                    "num": 1,
                    "rt": 1000,
                    "txval": 1000,
                    "igst": 180,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              }
            ]
          },
          {
            "ctin": "24BBBFF5679L8ZR",
            "trdnm": "Tiny Erp Private Limited",
            "supfildt": TEST_DATE.strftime("%d-%m-%Y"),
            "supprd": TEST_DATE.strftime("%m%Y"),
            "nt": [
              {
                "ntnum": "INV/011",
                "typ": "C",
                "suptyp": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 944.0,
                "pos": "01",
                "rev": "N",
                "itcavl": "N",
                "rsn": "C",
                "diffprcnt": 1,
                "srctyp": "e-Invoice",
                "irn": "897ADG56RTY78956HYUG90BNHHIJK453GFTD99845672FDHHHSHGFH4567FG56TR",
                "irngendate": "27-01-2023",
                "items": [
                  {
                    "num": 1,
                    "rt": 800,
                    "txval": 800,
                    "igst": 144,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              },
              {
                "ntnum": "INV/012",
                "typ": "C",
                "suptyp": "R",
                "dt": TEST_DATE.strftime("%d-%m-%Y"),
                "val": 1180.0,
                "pos": "01",
                "rev": "N",
                "itcavl": "N",
                "rsn": "C",
                "diffprcnt": 1,
                "srctyp": "e-Invoice",
                "irn": "897ADG56RTY78956HYUG90BNHHIJK453GFTD99845672FDHHHSHGFH4567FG56TR",
                "irngendate": "27-01-2023",
                "items": [
                  {
                    "num": 1,
                    "rt": 18,
                    "txval": 1000,
                    "igst": 180,
                    "cgst": 0,
                    "sgst": 0,
                    "cess": 0
                  }
                ]
              }
            ]
          }

        ],
        "impg": [
          {
            "refdt": "27-01-2023",
            "recdt": "27-01-2023",
            "portcode": "18272A",
            "boenum": "BOE/123",
            "boedt": TEST_DATE.strftime("%d-%m-%Y"),
            "isamd": "N",
            "txval": 100000,
            "igst": 18000,
            "cess": 0.0
          }
        ],
        "impgsez": [
          {
            "ctin": "19AAACR4849R3ZG",
            "trdnm": "GSTN",
            "boe": [
              {
                "refdt": "27-01-2023",
                "recdt": "27-01-2023",
                "portcode": "18272A",
                "boenum": "SEZ/123",
                "boedt": "27-01-2023",
                "isamd": "N",
                "txval": 100000,
                "igst": 18000,
                "cess": 0.0
              }
            ]
          }
        ]
      }
    }
  }
}
