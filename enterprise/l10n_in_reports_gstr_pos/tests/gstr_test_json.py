expected_gstr1_pos_response = {
    'gstin': '24AAGCC7144L6ZE',
    'fp': '052023',
    'b2b': [],
    'b2cl': [],
    'b2cs': [
        {
        'sply_ty': 'INTRA',
        'pos': '24',
        'typ': 'OE',
        'rt': 5.0,
        'txval': 400.0,
        'iamt': 0.0,
        'samt': 10.0,
        'camt': 10.0,
        'csamt': 0.0
        }
    ],
    'cdnr': [],
    'cdnur': [],
    'exp': [],
    'hsn': {
        'data': [
        {
            'hsn_sc': '1111',
            'uqc': 'UNT',
            'rt': 5,
            'qty': 2.0,
            'txval': 200.0,
            'iamt': 0.0,
            'samt': 5.0,
            'camt': 5.0,
            'csamt': 0.0,
            'num': 1
        },
        {
            'hsn_sc': '2222',
            'uqc': 'DOZ',
            'rt': 5,
            'qty': 1.0,
            'txval': 200.0,
            'iamt': 0.0,
            'samt': 5.0,
            'camt': 5.0,
            'csamt': 0.0,
            'num': 2
        }
        ]
    },
    "doc_issue": {
        "doc_det": []
    }
}

expected_gstr1_pos_response_old_period = {
    'gstin': '24AAGCC7144L6ZE',
    'fp': '042023',
    'b2b': [],
    'b2cl': [],
    'b2cs': [
        {
            'sply_ty': 'INTRA',
            'pos': '24',
            'typ': 'OE',
            'rt': 5.0,
            'txval': 1200.0,
            'iamt': 0.0,
            'samt': 30.0,
            'camt': 30.0,
            'csamt': 0.0
        }
    ],
    'cdnr': [],
    'cdnur': [],
    'exp': [],
    'doc_issue': {
        'doc_det': []
    },
    'hsn': {
        'data': [
            {
                'hsn_sc': '1111',
                'uqc': 'UNT',
                'rt': 5,
                'qty': 4.0,
                'txval': 400.0,
                'iamt': 0.0,
                'samt': 10.0,
                'camt': 10.0,
                'csamt': 0.0,
                'num': 1
            },
            {
                'hsn_sc': '2222',
                'uqc': 'DOZ',
                'rt': 5,
                'qty': 4.0,
                'txval': 800.0,
                'iamt': 0.0,
                'samt': 20.0,
                'camt': 20.0,
                'csamt': 0.0,
                'num': 2
            }
        ]
    }
}

expected_gstr1_pos_response_current_period = {
    'gstin': '24AAGCC7144L6ZE',
    'fp': '052023',
    'b2b': [
        {
            'ctin': '24ABCPM8965E1ZE',
            'inv': [
                {
                    'inum': 'INV/23-24/0001',
                    'idt': '20-05-2023',
                    'val': 630.0,
                    'pos': '24',
                    'rchrg': 'N',
                    'inv_typ': 'R',
                    'itms': [
                        {
                            'num': 1,
                            'itm_det': {
                                'txval': 600.0,
                                'iamt': 0.0,
                                'camt': 15.0,
                                'samt': 15.0,
                                'csamt': 0.0,
                                'rt': 5.0
                            }
                        }
                    ]
                }
            ]
        }
    ],
    'b2cl': [],
    'b2cs': [
        {
        'sply_ty': 'INTRA',
        'pos': '24',
        'typ': 'OE',
        'rt': 5.0,
        'txval': -600.0,
        'iamt': 0.0,
        'samt': -15.0,
        'camt': -15.0,
        'csamt': 0.0
        }
    ],
    'cdnr': [],
    'cdnur': [],
    'exp': [],
    'doc_issue': {
        'doc_det': []
    },
    'hsn': {
        'data': [
            {
                'hsn_sc': '1111',
                'uqc': 'UNT',
                'rt': 5,
                'qty': 0.0,
                'txval': 0.0,
                'iamt': 0.0,
                'samt': 0.0,
                'camt': 0.0,
                'csamt': 0.0,
                'num': 1
            },
            {
                'hsn_sc': '2222',
                'uqc': 'DOZ',
                'rt': 5,
                'qty': 0.0,
                'txval': 0.0,
                'iamt': 0.0,
                'samt': 0.0,
                'camt': 0.0,
                'csamt': 0.0,
                'num': 2
            }
        ]
    }
}

expected_pos_service_product_gstr1_response = {
    'gstin': '24AAGCC7144L6ZE',
    'fp': '052023',
    'b2b': [],
    'b2cl': [],
    'b2cs': [
        {
            'sply_ty': 'INTRA',
            'pos': '24',
            'typ': 'OE',
            'rt': 5.0,
            'txval': 400.0,
            'iamt': 0.0,
            'samt': 10.0,
            'camt': 10.0,
            'csamt': 0.0
        }
    ],
    'cdnr': [],
    'cdnur': [],
    'exp': [],
    'hsn': {
        'data': [
            {
                'hsn_sc': '1111',
                'uqc': 'UNT',
                'rt': 5,
                'qty': 2.0,
                'txval': 200.0,
                'iamt': 0.0,
                'samt': 5.0,
                'camt': 5.0,
                'csamt': 0.0,
                'num': 1
            },
            {
                'hsn_sc': '9911',
                'uqc': 'NA',
                'rt': 5,
                'qty': 0.0,
                'txval': 200.0,
                'iamt': 0.0,
                'samt': 5.0,
                'camt': 5.0,
                'csamt': 0.0,
                'num': 2
            }
        ]
    },
    'doc_issue': {
        'doc_det': []
    }
}
