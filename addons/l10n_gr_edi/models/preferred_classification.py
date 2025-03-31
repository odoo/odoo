from odoo import api, fields, models


CLASSIFICATION_MAP = {
    '1.1': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_002', 'E3_561_007', 'E3_563'),
        'category1_4': ('E3_880_001',),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566', 'E3_567', 'E3_568', 'E3_570',
                        'E3_561_002'),
        'category1_7': ('E3_881_001', 'E3_881_003', 'E3_881_004'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': ('E3_596', 'E3_597'),
        'category2_1': ('E3_102_001', 'E3_102_003', 'E3_102_006', 'E3_313_001', 'E3_313_005'),
        'category2_2': ('E3_202_001', 'E3_202_005', 'E3_302_001', 'E3_302_005'),
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_102_001', 'E3_102_003', 'E3_102_004', 'E3_102_005', 'E3_202_003',
                        'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003', 'E3_313_004', 'E3_581_003'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_882_001', 'E3_883_001', 'E3_102_001', 'E3_102_003', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_001', 'E3_883_001'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '1.2': {
        'category1_1': ('E3_561_005', 'E3_561_007'),
        'category1_2': ('E3_561_005', 'E3_561_007'),
        'category1_3': ('E3_561_005', 'E3_561_007'),
        'category1_4': ('E3_880_003',),
        'category1_5': ('E3_561_005', 'E3_561_007', 'E3_562', 'E3_570'),
        'category1_7': ('E3_881_003',),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '1.3': {
        'category1_1': ('E3_561_006', 'E3_561_007'),
        'category1_2': ('E3_561_006', 'E3_561_007'),
        'category1_3': ('E3_561_006', 'E3_561_007'),
        'category1_4': ('E3_880_004',),
        'category1_5': ('E3_561_006', 'E3_561_007', 'E3_562', 'E3_570'),
        'category1_7': ('E3_881_004',),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '1.4': {
        'category1_7': ('E3_881_001', 'E3_881_003', 'E3_881_004'),
        'category1_95': 'blank',
        'category2_1': ('E3_102_001', 'E3_102_003', 'E3_102_006', 'E3_313_001', 'E3_313_005'),
        'category2_2': ('E3_202_001', 'E3_202_005', 'E3_302_001', 'E3_302_005'),
        'category2_4': ('E3_585_002', 'E3_585_005', 'E3_585_006', 'E3_585_016', 'E3_102_004', 'E3_102_005',
                        'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003', 'E3_313_004',
                        'E3_581_003'),
        'category2_5': ('E3_585_002', 'E3_585_005', 'E3_585_006', 'E3_585_016', 'E3_882_001', 'E3_883_001',
                        'E3_102_004', 'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004',
                        'E3_313_003', 'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_001', 'E3_883_001'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '1.5': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_007'),
        'category1_4': ('E3_880_001', 'E3_880_003', 'E3_880_004'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category2_3': ('E3_585_009',),
        'category2_4': ('E3_585_009',),
        'category2_5': ('E3_585_009',),
        'category2_9': 'blank',
        'category2_10': 'all_above',
        'category2_11': 'all_above',
    },
    '1.6': 'associate',
    '2.1': {
        'category1_3': ('E3_561_001', 'E3_561_002', 'E3_561_007', 'E3_563'),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566', 'E3_567', 'E3_568', 'E3_570'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
        'category2_1': ('E3_102_001', 'E3_102_003', 'E3_102_006', 'E3_313_001', 'E3_313_005'),
        'category2_2': ('E3_202_001', 'E3_202_005', 'E3_302_001', 'E3_302_005'),
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_102_001', 'E3_102_003', 'E3_102_004', 'E3_102_005', 'E3_202_003',
                        'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003', 'E3_313_004', 'E3_581_003'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_882_001', 'E3_883_001', 'E3_102_001', 'E3_102_003', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_001', 'E3_883_001'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '2.2': {
        'category1_3': ('E3_561_005', 'E3_561_007', 'E3_563'),
        'category1_5': ('E3_561_005', 'E3_561_007', 'E3_562', 'E3_570'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '2.3': {
        'category1_3': ('E3_561_006', 'E3_561_007', 'E3_563'),
        'category1_5': ('E3_561_006', 'E3_561_007', 'E3_562', 'E3_570'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '2.4': 'associate',
    '3.1': {
        'category2_1': ('E3_102_002', 'E3_102_003', 'E3_102_006', 'E3_313_002', 'E3_313_005'),
        'category2_2': ('E3_202_002', 'E3_202_005', 'E3_302_002', 'E3_302_005'),
        'category2_3': ('E3_585_004', 'E3_585_009', 'E3_585_016'),
        'category2_5': ('E3_585_004', 'E3_585_016', 'E3_586'),
        'category2_7': ('E3_882_002', 'E3_883_002'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '3.2': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_007', 'E3_563'),
        'category1_4': ('E3_880_001',),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566', 'E3_567', 'E3_568', 'E3_570'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': ('E3_596', 'E3_597'),
        'category2_1': ('E3_102_001', 'E3_102_003', 'E3_102_006', 'E3_313_001', 'E3_313_005'),
        'category2_2': ('E3_202_001', 'E3_202_005', 'E3_302_001', 'E3_302_005'),
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_882_001', 'E3_883_001', 'E3_102_004', 'E3_102_005', 'E3_202_003',
                        'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003', 'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_001', 'E3_883_001'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '5.1': 'associate',
    '5.2': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_005', 'E3_561_006', 'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_005', 'E3_561_006', 'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_002', 'E3_561_005', 'E3_561_006', 'E3_561_007', 'E3_563'),
        'category1_4': ('E3_880_001', 'E3_880_003', 'E3_880_004'),
        'category1_5': ('E3_561_005', 'E3_561_006', 'E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566',
                        'E3_567', 'E3_568', 'E3_570', 'E3_561_002'),
        'category1_7': ('E3_881_001', 'E3_881_003', 'E3_881_004'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': ('E3_596', 'E3_597'),
        'category2_1': ('E3_102_001', 'E3_102_002', 'E3_102_003', 'E3_102_006', 'E3_313_001', 'E3_313_002',
                        'E3_313_005'),
        'category2_2': ('E3_202_001', 'E3_202_002', 'E3_202_005', 'E3_302_001', 'E3_302_002', 'E3_302_005'),
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_102_004', 'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003',
                        'E3_302_004', 'E3_313_003', 'E3_313_004', 'E3_581_003'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_882_001', 'E3_883_001', 'E3_102_004', 'E3_102_005', 'E3_202_003',
                        'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003', 'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_001', 'E3_882_002', 'E3_883_001', 'E3_883_002'),
        'category2_9': 'blank',
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '6.1': {
        'category1_6': ('E3_595',),
        'category1_95': 'blank',
    },
    '6.2': {
        'category1_6': ('E3_595',),
        'category1_95': 'blank',
    },
    '7.1': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_007'),
        'category1_4': ('E3_880_001',),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_570'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
        'category2_1': ('E3_102_001', 'E3_102_003', 'E3_102_006', 'E3_313_001', 'E3_313_005'),
        'category2_2': ('E3_202_001', 'E3_202_005', 'E3_302_001', 'E3_302_005'),
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_012', 'E3_585_011', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_102_004', 'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003',
                        'E3_302_004', 'E3_313_003', 'E3_313_004'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_004', 'E3_585_005', 'E3_585_006', 'E3_585_008',
                        'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015',
                        'E3_585_016', 'E3_586', 'E3_882_001', 'E3_883_001', 'E3_102_004', 'E3_102_005', 'E3_202_003',
                        'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003', 'E3_313_004'),
        'category2_7': ('E3_882_001', 'E3_883_001'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '8.1': {
        'category1_3': ('E3_561_001',),
        'category1_5': ('E3_562',),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
        'category2_4': ('E3_585_014', 'E3_585_016'),
        'category2_5': ('E3_585_014', 'E3_585_016'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '8.2': {
        'category1_95': 'blank',
        'category2_5': ('E3_585_005', 'E3_585_006', 'E3_585_016'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '11.1': {
        'category1_1': ('E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006', 'E3_561_007'),
        'category1_2': ('E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006', 'E3_561_007'),
        'category1_3': ('E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006', 'E3_561_007', 'E3_563'),
        'category1_4': ('E3_880_002', 'E3_880_003', 'E3_880_004', 'E3_561_007'),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_570'),
        'category1_7': ('E3_881_002', 'E3_881_003', 'E3_881_004'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '11.2': {
        'category1_3': ('E3_561_003', 'E3_561_005', 'E3_561_006', 'E3_561_007', 'E3_563'),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_570'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '11.3': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                        'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                        'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                        'E3_561_007', 'E3_563'),
        'category1_4': ('E3_880_002', 'E3_880_003', 'E3_880_004', 'E3_561_007'),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_570'),
        'category1_7': ('E3_881_002', 'E3_881_003', 'E3_881_004'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '11.4': {
        'category1_1': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                        'E3_561_007'),
        'category1_2': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                        'E3_561_007'),
        'category1_3': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                        'E3_561_007', 'E3_563'),
        'category1_4': ('E3_880_002', 'E3_880_003', 'E3_880_004', 'E3_561_007'),
        'category1_5': ('E3_561_007', 'E3_562', 'E3_563', 'E3_570'),
        'category1_7': ('E3_881_002', 'E3_881_003', 'E3_881_004'),
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_95': 'blank',
    },
    '11.5': {
        'category1_7': ('E3_881_002', 'E3_881_003', 'E3_881_004'),
        'category1_95': 'blank',
    },
    '13.1': {
        'category2_1': ('E3_102_002', 'E3_102_006', 'E3_313_002', 'E3_313_005'),
        'category2_2': ('E3_202_002', 'E3_202_005', 'E3_302_002', 'E3_302_005'),
        'category2_3': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_002', 'E3_883_002', 'E3_102_002', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_5': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_002', 'E3_883_002', 'E3_102_002', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_002', 'E3_883_002'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '13.2': {
        'category2_3': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_002', 'E3_883_002', 'E3_102_002', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_5': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_002', 'E3_883_002', 'E3_102_002', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '13.3': {
        'category2_3': ('E3_585_016',),
        'category2_5': ('E3_585_016',),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '13.4': {
        'category2_3': ('E3_585_016',),
        'category2_5': ('E3_585_016',),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '13.30': {
        'category2_3': ('E3_585_016', 'E3_586'),
        'category2_5': ('E3_585_016', 'E3_586', 'E3_588'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '13.31': {
        'category2_1': ('E3_102_002', 'E3_102_006', 'E3_313_002', 'E3_313_005'),
        'category2_2': ('E3_202_002', 'E3_202_005', 'E3_302_002', 'E3_302_005'),
        'category2_3': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_002', 'E3_883_002', 'E3_102_002', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_5': ('E3_585_005', 'E3_585_006', 'E3_585_009', 'E3_585_011', 'E3_585_012', 'E3_585_013',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_002', 'E3_883_002', 'E3_102_002', 'E3_102_004',
                        'E3_102_005', 'E3_202_003', 'E3_202_004', 'E3_302_003', 'E3_302_004', 'E3_313_003',
                        'E3_313_004', 'E3_581_003'),
        'category2_7': ('E3_882_002', 'E3_883_002'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.1': {
        'category2_1': ('E3_102_004', 'E3_102_006', 'E3_313_003', 'E3_313_005'),
        'category2_2': ('E3_202_003', 'E3_202_005', 'E3_302_003', 'E3_302_005'),
        'category2_4': ('E3_585_002', 'E3_585_003', 'E3_585_016', 'E3_882_003', 'E3_883_003', 'E3_581_003'),
        'category2_5': ('E3_585_002', 'E3_585_003', 'E3_585_016', 'E3_882_003', 'E3_883_003', 'E3_581_003'),
        'category2_7': ('E3_882_003', 'E3_883_003'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.2': {
        'category2_1': ('E3_102_005', 'E3_102_006', 'E3_313_004', 'E3_313_005'),
        'category2_2': ('E3_202_004', 'E3_202_005', 'E3_302_004', 'E3_302_005'),
        'category2_4': ('E3_585_002', 'E3_585_003', 'E3_585_016', 'E3_882_004', 'E3_883_004', 'E3_581_003'),
        'category2_5': ('E3_585_002', 'E3_585_003', 'E3_585_016', 'E3_882_004', 'E3_883_004', 'E3_581_003'),
        'category2_7': ('E3_882_004', 'E3_883_004'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.3': {
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_102_004', 'E3_102_006', 'E3_202_003',
                        'E3_202_005', 'E3_302_003', 'E3_302_005', 'E3_313_003', 'E3_313_005', 'E3_581_003'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_003', 'E3_883_003', 'E3_102_004',
                        'E3_102_006', 'E3_202_003', 'E3_202_005', 'E3_302_003', 'E3_302_005', 'E3_313_003',
                        'E3_313_005', 'E3_581_003'),
        'category2_7': ('E3_882_003', 'E3_883_003'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.4': {
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_581_003'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_102_005', 'E3_102_006', 'E3_202_004',
                        'E3_202_005', 'E3_302_004', 'E3_302_005', 'E3_313_004', 'E3_313_005', 'E3_581_003'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_882_004', 'E3_883_004', 'E3_102_005',
                        'E3_102_006', 'E3_202_004', 'E3_202_005', 'E3_302_004', 'E3_302_005', 'E3_313_004',
                        'E3_313_005', 'E3_581_003'),
        'category2_7': ('E3_882_004', 'E3_883_004'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.5': {
        'category2_5': ('E3_585_007', 'E3_588'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.30': {
        'category2_3': ('E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_016', 'E3_586'),
        'category2_4': ('E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_016', 'E3_586'),
        'category2_5': ('E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_016', 'E3_586'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '14.31': {
        'category2_1': ('E3_102_004', 'E3_102_005', 'E3_102_006', 'E3_313_003', 'E3_313_004', 'E3_313_005'),
        'category2_2': ('E3_202_003', 'E3_202_004', 'E3_202_005', 'E3_302_003', 'E3_302_004', 'E3_302_005'),
        'category2_3': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_015', 'E3_585_016', 'E3_586',
                        'E3_581_003'),
        'category2_4': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_010', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_015', 'E3_585_016', 'E3_586',
                        'E3_102_004', 'E3_102_005', 'E3_102_006', 'E3_202_003', 'E3_202_004', 'E3_202_005',
                        'E3_302_003', 'E3_302_004', 'E3_302_005', 'E3_313_003', 'E3_313_004', 'E3_313_005',
                        'E3_581_003', 'E3_882_003', 'E3_883_003', 'E3_882_004', 'E3_883_004'),
        'category2_5': ('E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005', 'E3_585_006',
                        'E3_585_007', 'E3_585_010', 'E3_585_011', 'E3_585_012', 'E3_585_013', 'E3_585_014',
                        'E3_585_015', 'E3_585_016', 'E3_586', 'E3_102_004', 'E3_102_005', 'E3_102_006', 'E3_202_003',
                        'E3_202_004', 'E3_202_005', 'E3_302_003', 'E3_302_004', 'E3_302_005', 'E3_313_003',
                        'E3_313_004', 'E3_313_005', 'E3_581_003', 'E3_882_003', 'E3_882_004', 'E3_883_003',
                        'E3_883_004'),
        'category2_7': ('E3_882_003', 'E3_882_004', 'E3_883_003', 'E3_883_004'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '15.1': {
        'category2_1': ('E3_102_002', 'E3_102_006', 'E3_313_002', 'E3_313_005'),
        'category2_2': ('E3_202_002', 'E3_202_005', 'E3_302_002', 'E3_302_005'),
        'category2_3': ('E3_585_004', 'E3_585_016'),
        'category2_5': ('E3_585_004', 'E3_585_016'),
        'category2_7': ('E3_882_002', 'E3_883_002'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '16.1': {
        'category2_5': ('E3_585_014', 'E3_585_016'),
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_95': 'blank',
    },
    '17.1': {
        'category2_6': ('E3_581_001', 'E3_581_002', 'E3_581_003'),
        'category2_95': 'blank',
    },
    '17.2': {
        'category2_8': ('E3_587',),
        'category2_95': 'blank',
    },
    '17.3': {
        'category1_8': 'all_above',
        'category1_9': 'all_above',
        'category1_10': ('E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004', 'E3_561_005', 'E3_561_006',
                         'E3_561_007', 'E3_562', 'E3_563', 'E3_595', 'E3_596', 'E3_597', 'E3_880_001', 'E3_880_002',
                         'E3_880_003', 'E3_880_004', 'E3_881_001', 'E3_881_002', 'E3_881_003', 'E3_881_004', 'E3_564',
                         'E3_565', 'E3_566', 'E3_567', 'E3_568', 'E3_570'),
        'category1_95': 'blank',
    },
    '17.4': {
        'category1_10': 'blank',
        'category1_95': 'blank',
    },
    '17.5': {
        'category2_10': 'all_above',
        'category2_11': 'all_above',
        'category2_12': (
            'E3_102_001', 'E3_102_002', 'E3_102_003', 'E3_102_004', 'E3_102_005', 'E3_102_006', 'E3_202_001',
            'E3_202_002', 'E3_202_003', 'E3_202_004', 'E3_202_005', 'E3_302_001', 'E3_302_002', 'E3_302_003',
            'E3_302_004', 'E3_302_005', 'E3_313_001', 'E3_313_002', 'E3_313_003', 'E3_313_004', 'E3_313_005',
            'E3_581_001', 'E3_581_002', 'E3_581_003', 'E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004',
            'E3_585_005', 'E3_585_006', 'E3_585_007', 'E3_585_008', 'E3_585_009', 'E3_585_010', 'E3_585_011',
            'E3_585_012', 'E3_585_013', 'E3_585_014', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_587', 'E3_882_001',
            'E3_882_002', 'E3_882_003', 'E3_882_004', 'E3_883_001', 'E3_883_002', 'E3_883_003', 'E3_883_004', 'E3_582',
            'E3_583', 'E3_584', 'E3_588', 'E3_589', 'E3_103', 'E3_203', 'E3_303', 'E3_208', 'E3_308', 'E3_314',
            'XE3_106', 'XE3_205', 'XE3_305', 'XE3_210', 'XE3_310', 'XE3_318'
        ),
        'category2_13': ('E3_101', 'E3_201', 'E3_301', 'E3_207', 'E3_307', 'E3_312'),
        'category2_14': ('E3_104', 'E3_204', 'E3_304', 'E3_209', 'E3_309', 'E3_315'),
        'category2_95': 'blank',
    },
    '17.6': {
        'category2_12': 'blank',
        'category2_95': 'blank',
    },
}

INVOICE_TYPES_SELECTION = [
    ('1.1', '1.1 - Sales Invoice'),
    ('1.2', '1.2 - Sales Invoice/Intra-community Supplies'),
    ('1.3', '1.3 - Sales Invoice/Third Country Supplies'),
    ('1.4', '1.4 - Sales Invoice/Sale on Behalf of Third Parties'),
    ('1.5', '1.5 - Sales Invoice/Clearance of Sales on Behalf of Third Parties – Fees from Sales on Behalf of Third Parties'),
    ('1.6', '1.6 - Sales Invoice/Supplemental Accounting Source Document'),
    ('2.1', '2.1 - Service Rendered Invoice'),
    ('2.2', '2.2 - Intra-community Service Rendered Invoice'),
    ('2.3', '2.3 - Third Country Service Rendered Invoice'),
    ('2.4', '2.4 - Service Rendered Invoice/Supplemental Accounting Source Document'),
    ('3.1', '3.1 - Proof of Expenditure (non-liable Issuer)'),
    ('3.2', '3.2 - Proof of Expenditure (denial of issuance by liable Issuer)'),
    ('5.1', '5.1 - Credit Invoice/Associated'),
    ('5.2', '5.2 - Credit Invoice/Non-Associated'),
    ('6.1', '6.1 - Self-Delivery Record'),
    ('6.2', '6.2 - Self-Supply Record'),
    ('7.1', '7.1 - Contract – Income'),
    ('8.1', '8.1 - Rents – Income'),
    ('8.2', '8.2 - Special Record – Accommodation Tax Collection/Payment Receipt'),
    ('11.1', '11.1 - Retail Sales Receipt'),
    ('11.2', '11.2 - Service Rendered Receipt'),
    ('11.3', '11.3 - Simplified Invoice'),
    ('11.4', '11.4 - Retail Sales Credit Note'),
    ('11.5', '11.5 - Retail Sales Receipt on Behalf of Third Parties'),
    ('13.1', '13.1 - Expenses – Domestic/Foreign Retail Transaction Purchases'),
    ('13.2', '13.2 - Domestic/Foreign Retail Transaction Provision'),
    ('13.3', '13.3 - Shared Utility Bills'),
    ('13.4', '13.4 - Subscriptions'),
    ('13.30', '13.30 - Self-Declared Entity Accounting Source Documents (Dynamic)'),
    ('13.31', '13.31 - Domestic/Foreign Retail Sales Credit Note'),
    ('14.1', '14.1 - Invoice/Intra-community Acquisitions'),
    ('14.2', '14.2 - Invoice/Third Country Acquisitions'),
    ('14.3', '14.3 - Invoice/Intra-community Services Receipt'),
    ('14.4', '14.4 - Invoice/Third Country Services Receipt'),
    ('14.5', '14.5 - EFKA'),
    ('14.30', '14.30 - Self-Declared Entity Accounting Source Documents (Dynamic)'),
    ('14.31', '14.31 - Domestic/Foreign Credit Note'),
    ('15.1', '15.1 - Contract-Expense'),
    ('16.1', '16.1 - Rent-Expense'),
    ('17.1', '17.1 - Payroll'),
    ('17.2', '17.2 - Amortisations'),
    ('17.3', '17.3 - Other Income Adjustment/Regularisation Entries – Accounting Base'),
    ('17.4', '17.4 - Other Income Adjustment/Regularisation Entries – Tax Base'),
    ('17.5', '17.5 - Other Expense Adjustment/Regularisation Entries – Accounting Base'),
    ('17.6', '17.6 - Other Expense Adjustment/Regularisation Entries – Tax Base'),
]

CLASSIFICATION_CATEGORY_SELECTION = [
    # Income classification categories
    ('category1_1', 'category1_1 - Commodity Sale Income (+)/(-)'),
    ('category1_2', 'category1_2 - Product Sale Income (+)/(-)'),
    ('category1_3', 'category1_3 - Provision of Services Income (+)/(-)'),
    ('category1_4', 'category1_4 - Sale of Fixed Assets Income (+)/(-)'),
    ('category1_5', 'category1_5 - Other Income/Profits(+)/(-)'),
    ('category1_6', 'category1_6 - Self-Deliveries/Self-Supplies (+)/(-)'),
    ('category1_7', 'category1_7 - Income on behalf of Third Parties (+)/(-)'),
    ('category1_8', 'category1_8 - Past fiscal years income (+)/(-)'),
    ('category1_9', 'category1_9 - Future fiscal years income (+)/(-)'),
    ('category1_10', 'category1_10 - Other Income Adjustment/Regularisation Entries (+)/(-)'),
    ('category1_95', 'category1_95 - Other Income-related Information (+)/(-)'),

    # Expense classification categories
    ('category2_1', 'category2_1 - Commodity Purchases(+)/(-)'),
    ('category2_2', 'category2_2 - Raw and Adjuvant Material Purchases (+)/(-)'),
    ('category2_3', 'category2_3 - Services Receipt (+)/(-)'),
    ('category2_4', 'category2_4 - General Expenses Subject to VAT Deduction (+)/(-)'),
    ('category2_5', 'category2_5 - General Expenses Not Subject to VAT Deduction (+)/(-)'),
    ('category2_6', 'category2_6 - Personnel Fees and Benefits (+)/(-)'),
    ('category2_7', 'category2_7 - Fixed Asset Purchases (+)/(-)'),
    ('category2_8', 'category2_8 - Fixed Asset Amortisations (+)/(-)'),
    ('category2_9', 'category2_9 - Expenses on behalf of Third Parties (+)/(-)'),
    ('category2_10', 'category2_10 - Past fiscal years expenses (+)/(-)'),
    ('category2_11', 'category2_11 - Future fiscal years expenses (+)/(-)'),
    ('category2_12', 'category2_12 - Other Expense Adjustment/Regularisation Entries(+)/(-)'),
    ('category2_13', 'category2_13 - Stock at Period Start (+)/(-)'),
    ('category2_14', 'category2_14 - Stock at Period End (+)/(-)'),
    ('category2_95', 'category2_95 - Other Expense-related Information (+)/(-)'),
]

CLASSIFICATION_TYPE_SELECTION = [
    # Income classification types
    ('E3_106', 'E3_106 - Self-Production of Fixed Assets – Self-Deliveries – Destroying inventory/Commodities'),
    ('E3_205', 'E3_205 - Self-Production of Fixed Assets – Self-Deliveries – Destroying inventory/Raw and other materials'),
    ('E3_210', 'E3_210 - Self-Production of Fixed Assets – Self-Deliveries – Destroying inventory/Products and production in progress'),
    ('E3_305', 'E3_305 - Self-Production of Fixed Assets – Self-Deliveries – Destroying inventory/Raw and other materials'),
    ('E3_310', 'E3_310 - Self-Production of Fixed Assets – Self-Deliveries – Destroying inventory/Products and production in progress'),
    ('E3_318', 'E3_318 - Self-Production of Fixed Assets – Self-Deliveries – Destroying inventory/Production expenses'),
    ('E3_561_001', 'E3_561_001 - Wholesale Sales of Goods and Services – for Traders'),
    ('E3_561_002', 'E3_561_002 - Wholesale Sales of Goods and Services pursuant to article 39a paragraph 5 of the VAT Code (Law 2859/2000)'),
    ('E3_561_003', 'E3_561_003 - Retail Sales of Goods and Services – Private Clientele'),
    ('E3_561_004', 'E3_561_004 - Retail Sales of Goods and Services pursuant to article 39a paragraph 5 of the VAT Code (Law 2859/2000)'),
    ('E3_561_005', 'E3_561_005 - Intra-Community Foreign Sales of Goods and Services'),
    ('E3_561_006', 'E3_561_006 - Third Country Foreign Sales of Goods and Services'),
    ('E3_561_007', 'E3_561_007 - Other Sales of Goods and Services'),
    ('E3_562', 'E3_562 - Other Ordinary Income'),
    ('E3_563', 'E3_563 - Credit Interest and Related Income'),
    ('E3_564', 'E3_564 - Credit Exchange Differences'),
    ('E3_565', 'E3_565 - Income from Participations'),
    ('E3_566', 'E3_566 - Profits from Disposing Non-Current Assets'),
    ('E3_567', 'E3_567 - Profits from the Reversal of Provisions and Impairments'),
    ('E3_568', 'E3_568 - Profits from Measurement at Fair Value'),
    ('E3_570', 'E3_570 - Extraordinary income and profits'),
    ('E3_595', 'E3_595 - Self-Production Expenses'),
    ('E3_596', 'E3_596 - Subsidies - Grants'),
    ('E3_597', 'E3_597 - Subsidies – Grants for Investment Purposes – Expense Coverage'),
    ('E3_880_001', 'E3_880_001 - Wholesale Sales of Fixed Assets'),
    ('E3_880_002', 'E3_880_002 - Retail Sales of Fixed Assets'),
    ('E3_880_003', 'E3_880_003 - Intra-Community Foreign Sales of Fixed Assets'),
    ('E3_880_004', 'E3_880_004 - Third Country Foreign Sales of Fixed Assets'),
    ('E3_881_001', 'E3_881_001 - Wholesale Sales on behalf of Third Parties'),
    ('E3_881_002', 'E3_881_002 - Retail Sales on behalf of Third Parties'),
    ('E3_881_003', 'E3_881_003 - Intra-Community Foreign Sales on behalf of Third Parties'),
    ('E3_881_004', 'E3_881_004 - Third Country Foreign Sales on behalf of Third Parties'),
    ('E3_598_001', 'E3_598_001 - Sales of goods belonging to excise duty'),
    ('E3_598_003', 'E3_598_003 - Sales on behalf of farmers through an agricultural cooperative e.t.c.'),

    # Expense classification types
    ('E3_101', 'E3_101 - Commodities at Period Start'),
    ('E3_102_001', 'E3_102_001 - Fiscal Year Commodity Purchases (net amount)/Wholesale'),
    ('E3_102_002', 'E3_102_002 - Fiscal Year Commodity Purchases (net amount)/Retail'),
    ('E3_102_003', 'E3_102_003 - Fiscal Year Commodity Purchases (net amount)/Goods under article 39a paragraph 5 of the VAT Code (Law 2859/2000)'),
    ('E3_102_004', 'E3_102_004 - Fiscal Year Commodity Purchases (net amount)/Foreign, Intra-Community'),
    ('E3_102_005', 'E3_102_005 - Fiscal Year Commodity Purchases (net amount)/Foreign, Third Countries'),
    ('E3_102_006', 'E3_102_006 - Fiscal Year Commodity Purchases (net amount)/Others'),
    ('E3_104', 'E3_104 - Commodities at Period End'),
    ('E3_201', 'E3_201 - Raw and Other Materials at Period Start/Production'),
    ('E3_202_001', 'E3_202_001 - Fiscal Year Raw and Other Material Purchases (net amount)/Wholesale'),
    ('E3_202_002', 'E3_202_002 - Fiscal Year Raw and Other Material Purchases (net amount)/Retail'),
    ('E3_202_003', 'E3_202_003 - Fiscal Year Raw and Other Material Purchases (net amount)/ Foreign, Intra-Community'),
    ('E3_202_004', 'E3_202_004 - Fiscal Year Raw and Other Material Purchases (net amount)/ Foreign, Third Countries'),
    ('E3_202_005', 'E3_202_005 - Fiscal Year Raw and Other Material Purchases (net amount)/Others'),
    ('E3_204', 'E3_204 - Raw and Other Material Stock at Period End/Production'),
    ('E3_207', 'E3_207 - Products and Production in Progress at Period Start/Production'),
    ('E3_209', 'E3_209 - Products and Production in Progress at Period End/Production'),
    ('E3_301', 'E3_301 - Raw and Other Material at Period Start/Agricultural'),
    ('E3_302_001', 'E3_302_001 - Fiscal Year Raw and Other Material Purchases (net amount)/Wholesale'),
    ('E3_302_002', 'E3_302_002 - Fiscal Year Raw and Other Material Purchases (net amount)/Retail'),
    ('E3_302_003', 'E3_302_003 - Fiscal Year Raw and Other Material Purchases (net amount)/Foreign, Intra-Community'),
    ('E3_302_004', 'E3_302_004 - Fiscal Year Raw and Other Material Purchases (net amount)/Foreign, Third Countries'),
    ('E3_302_005', 'E3_302_005 - Fiscal Year Raw and Other Material Purchases (net amount)/Others'),
    ('E3_304', 'E3_304 - Raw and Other Material Stock at Period End/Agricultural'),
    ('E3_307', 'E3_307 - Products and Production in Progress at Period Start/ Agricultural'),
    ('E3_309', 'E3_309 - Products and Production in Progress at Period End/ Agricultural'),
    ('E3_312', 'E3_312 - Stock at Period Start (Animals-Plants)'),
    ('E3_313_001', 'E3_313_001 - Animal-Plant Purchases (net amount)/Wholesale'),
    ('E3_313_002', 'E3_313_002 - Animal-Plant Purchases (net amount)/Retail'),
    ('E3_313_003', 'E3_313_003 - Animal-Plant Purchases (net amount)/ Foreign, Intra-Community'),
    ('E3_313_004', 'E3_313_004 - Animal-Plant Purchases (net amount)/ Foreign, Third Countries'),
    ('E3_313_005', 'E3_313_005 - Animal-Plant Purchases/Others'),
    ('E3_315', 'E3_315 - Stock at Period End (Animals-Plants)/Agricultural'),
    ('E3_581_001', 'E3_581_001 - Employee Benefits/Gross Earnings'),
    ('E3_581_002', 'E3_581_002 - Employee Benefits/Employer Contributions'),
    ('E3_581_003', 'E3_581_003 - Employee Benefits/Other Benefits'),
    ('E3_582', 'E3_582 - Asset Measurement Damages'),
    ('E3_583', 'E3_583 - Debit Exchange Differences'),
    ('E3_584', 'E3_584 - Damages from Disposing-Withdrawing Non-Current Assets'),
    ('E3_585_001', 'E3_585_001 - Foreign/Domestic Management Fees'),
    ('E3_585_002', 'E3_585_002 - Expenditures from Linked Enterprises'),
    ('E3_585_003', 'E3_585_003 - Expenditures from Non-Cooperative States or Privileged Tax Regimes'),
    ('E3_585_004', 'E3_585_004 - Expenditures for Information Day-Events'),
    ('E3_585_005', 'E3_585_005 - Reception and Hospitality Expenses'),
    ('E3_585_006', 'E3_585_006 - Travel expenses'),
    ('E3_585_007', 'E3_585_007 - Self-Employed Social Security Contributions'),
    ('E3_585_008', 'E3_585_008 - Commission Agent Expenses and Fees on behalf of Farmers'),
    ('E3_585_009', 'E3_585_009 - Other Fees for Domestic Services'),
    ('E3_585_010', 'E3_585_010 - Other Fees for Foreign Services'),
    ('E3_585_011', 'E3_585_011 - Energy'),
    ('E3_585_012', 'E3_585_012 - Water'),
    ('E3_585_013', 'E3_585_013 - Telecommunications'),
    ('E3_585_014', 'E3_585_014 - Rents'),
    ('E3_585_015', 'E3_585_015 - Advertisement and promotion'),
    ('E3_585_016', 'E3_585_016 - Other expenses'),
    ('E3_586', 'E3_586 - Debit interests and related expenses'),
    ('E3_587', 'E3_587 - Amortisations'),
    ('E3_588', 'E3_588 - Extraordinary expenses, damages and fines'),
    ('E3_589', 'E3_589 - Provisions (except for Personnel Provisions)'),
    ('E3_882_001', 'E3_882_001 - Fiscal Year Tangible Asset Purchases/Wholesale'),
    ('E3_882_002', 'E3_882_002 - Fiscal Year Tangible Asset Purchases/Retail'),
    ('E3_882_003', 'E3_882_003 - Fiscal Year Tangible Asset Purchases/ Intra-Community Foreign'),
    ('E3_882_004', 'E3_882_004 - Fiscal Year Tangible Asset Purchases/ Third Country Foreign'),
    ('E3_883_001', 'E3_883_001 - Fiscal Year Intangible Asset Purchases/Wholesale'),
    ('E3_883_002', 'E3_883_002 - Fiscal Year Intangible Asset Purchases/Retail'),
    ('E3_883_003', 'E3_883_003 - Fiscal Year Intangible Asset Purchases/ Intra-Community Foreign'),
    ('E3_883_004', 'E3_883_004 - Fiscal Year Intangible Asset Purchases/ Third Country Foreign'),
    ('E3_103', 'E3_103 - Impairment of goods'),
    ('E3_203', 'E3_203 - Impairment of raw materials and supplies'),
    ('E3_303', 'E3_303 - Impairment of raw materials and supplies'),
    ('E3_208', 'E3_208 - Impairment of products and production in progress'),
    ('E3_308', 'E3_308 - Impairment of products and production in progress'),
    ('E3_314', 'E3_314 - Impairment of animals-plants - goods'),
    ('XE3_106', 'E3_106 - Own production of fixed assets – Self Deliveries – Inventory Disasters'),
    ('XE3_205', 'E3_205 - Own production of fixed assets - Self Deliveries – Inventory Disasters'),
    ('XE3_305', 'E3_305 - Own production of fixed assets - Self Deliveries – Inventory Disasters'),
    ('XE3_210', 'E3_210 - Own production of fixed assets - Self Deliveries – Inventory Disasters'),
    ('XE3_310', 'E3_310 - Own production of fixed assets - Self Deliveries – Inventory Disasters'),
    ('XE3_318', 'E3_318 - Own production of fixed assets - Self Deliveries – Inventory Disasters'),
    ('E3_598_002', 'E3_598_002 - Purchases of goods falling into excise duty'),
]

CLASSIFICATION_VAT_SELECTION = [
    ('VAT_361', 'VAT_361 - Domestic Purchases & Expenditures'),
    ('VAT_362', 'VAT_362 - Purchases & Imports of Investment Goods (Fixed Assets)'),
    ('VAT_363', 'VAT_363 - Other Imports except for Investment Goods (Fixed Assets)'),
    ('VAT_364', 'VAT_364 - Intra-Community Goods Acquisitions'),
    ('VAT_365', 'VAT_365 - Intra-Community Services Receipts per article 14.2.a'),
    ('VAT_366', 'VAT_366 - Other Recipient Actions'),
]

TAX_EXEMPTION_CATEGORY_SELECTION = [
    ('1', '1 - Without VAT - article 3 of the VAT code'),
    ('2', '2 - Without VAT - article 5 of the VAT code'),
    ('3', '3 - Without VAT - article 13 of the VAT code'),
    ('4', '4 - Without VAT - article 14 of the VAT code'),
    ('5', '5 - Without VAT - article 16 of the VAT code'),
    ('6', '6 - Without VAT - article 19 of the VAT code'),
    ('7', '7 - Without VAT - article 22 of the VAT code'),
    ('8', '8 - Without VAT - article 24 of the VAT code'),
    ('9', '9 - Without VAT - article 25 of the VAT code'),
    ('10', '10 - Without VAT - article 26 of the VAT code'),
    ('11', '11 - Without VAT - article 27 of the VAT code'),
    ('12', '12 - Without VAT - article 27 - Seagoing Vessels of the VAT code'),
    ('13', '13 - Without VAT - article 27.1.γ - Seagoing Vessels of the VAT code'),
    ('14', '14 - Without VAT - article 28 of the VAT code'),
    ('15', '15 - Without VAT - article 39 of the VAT code'),
    ('16', '16 - Without VAT - article 39a of the VAT code'),
    ('17', '17 - Without VAT - article 40 of the VAT code'),
    ('18', '18 - Without VAT - article 41 of the VAT code'),
    ('19', '19 - Without VAT - article 47 of the VAT code'),
    ('20', '20 - VAT included - article 43 of the VAT code'),
    ('21', '21 - VAT included - article 44 of the VAT code'),
    ('22', '22 - VAT included - article 45 of the VAT code'),
    ('23', '23 - VAT included - article 46 of the VAT code'),
    ('24', '24 - Without VAT - article 6 of the VAT code'),
    ('25', '25 - Without VAT - ΠΟΛ.1029 / 1995'),
    ('26', '26 - Without VAT - ΠΟΛ.1167 / 2015'),
    ('27', '27 - Without VAT – Other VAT exceptions'),
    ('28', '28 - Without VAT - Article 24 (b)(1) of the VAT Code(Tax Free)'),
    ('29', '29 - Without VAT - Article 47 b of the VAT Code(OSS non - EU scheme)'),
    ('30', '30 - Without VAT - Article 47 c of the VAT Code(OSS EU scheme)'),
    ('31', '31 - Excluding VAT - Article 47 d of the VAT Code(IOSS)'),
]

PAYMENT_METHOD_SELECTION = [
    ('1', '1 - Domestic Payments Account Number'),
    ('2', '2 - Foreign Payments Account Number'),
    ('3', '3 - Cash'),
    ('4', '4 - Check'),
    ('5', '5 - On credit'),
    ('6', '6 - Web Banking'),
    ('7', '7 - POS / e-POS'),
]

INVOICE_TYPES_HAVE_INCOME = (
    '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '2.1', '2.2', '2.3', '2.4', '3.1', '3.2', '5.1', '5.2', '6.1', '6.2',
    '7.1', '8.1', '8.2', '11.1', '11.2', '11.3', '11.4', '11.5', '17.3', '17.4',
)

INVOICE_TYPES_HAVE_EXPENSE = (
    '1.1', '1.4', '1.5', '1.6', '2.1', '2.4', '3.1', '3.2', '5.1', '5.2', '7.1', '8.1', '8.2', '13.1', '13.2', '13.3',
    '13.4', '13.30', '13.31', '14.1', '14.2', '14.3', '14.4', '14.5', '14.30', '14.31', '15.1', '16.1', '17.1', '17.2',
    '17.5', '17.6',
)

CLASSIFICATION_CATEGORY_INCOME = (
    'category1_1', 'category1_2', 'category1_3', 'category1_4', 'category1_5', 'category1_6', 'category1_7',
    'category1_8', 'category1_9', 'category1_10', 'category1_95',
)

CLASSIFICATION_CATEGORY_EXPENSE = (
    'category2_1', 'category2_2', 'category2_3', 'category2_4', 'category2_5', 'category2_6', 'category2_7',
    'category2_8', 'category2_9', 'category2_10', 'category2_11', 'category2_12', 'category2_13', 'category2_14',
    'category2_95',
)

CLASSIFICATION_TYPE_INCOME = (
    'E3_106', 'E3_205', 'E3_210', 'E3_305', 'E3_310', 'E3_318', 'E3_561_001', 'E3_561_002', 'E3_561_003', 'E3_561_004',
    'E3_561_005', 'E3_561_006', 'E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566', 'E3_567', 'E3_568',
    'E3_570', 'E3_595', 'E3_596', 'E3_597', 'E3_880_001', 'E3_880_002', 'E3_880_003', 'E3_880_004', 'E3_881_001',
    'E3_881_002', 'E3_881_003', 'E3_881_004', 'E3_598_001', 'E3_598_003',
)

CLASSIFICATION_TYPE_EXPENSE = (
    'E3_101', 'E3_102_001', 'E3_102_002', 'E3_102_003', 'E3_102_004', 'E3_102_005', 'E3_102_006', 'E3_104', 'E3_201',
    'E3_202_001', 'E3_202_002', 'E3_202_003', 'E3_202_004', 'E3_202_005', 'E3_204', 'E3_207', 'E3_209', 'E3_301',
    'E3_302_001', 'E3_302_002', 'E3_302_003', 'E3_302_004', 'E3_302_005', 'E3_304', 'E3_307', 'E3_309', 'E3_312',
    'E3_313_001', 'E3_313_002', 'E3_313_003', 'E3_313_004', 'E3_313_005', 'E3_315', 'E3_581_001', 'E3_581_002',
    'E3_581_003', 'E3_582', 'E3_583', 'E3_584', 'E3_585_001', 'E3_585_002', 'E3_585_003', 'E3_585_004', 'E3_585_005',
    'E3_585_006', 'E3_585_007', 'E3_585_008', 'E3_585_009', 'E3_585_010', 'E3_585_011', 'E3_585_012', 'E3_585_013',
    'E3_585_014', 'E3_585_015', 'E3_585_016', 'E3_586', 'E3_587', 'E3_588', 'E3_589', 'E3_882_001', 'E3_882_002',
    'E3_882_003', 'E3_882_004', 'E3_883_001', 'E3_883_002', 'E3_883_003', 'E3_883_004', 'VAT_361', 'VAT_362', 'VAT_363',
    'VAT_364', 'VAT_365', 'VAT_366', 'E3_103', 'E3_203', 'E3_303', 'E3_208', 'E3_308', 'E3_314', 'XE3_106', 'XE3_205',
    'XE3_305', 'XE3_210', 'XE3_310', 'XE3_318', 'E3_598_002',
)

ALL_INVOICE_TYPES: tuple[str] = tuple(inv_type for inv_type, _ in INVOICE_TYPES_SELECTION)

TYPES_WITH_SEND_EXPENSE = ('3.1', '3.2')

TYPES_WITH_CORRELATE_INVOICE = ('1.6', '2.4', '5.1')

TYPES_WITH_VAT_EXEMPT = ('3.1', '3.2')

TYPES_WITH_FORBIDDEN_COUNTERPART = ('11.1', '11.2', '11.3', '11.4', '11.5', '17.3', '17.4')

TYPES_WITH_MANDATORY_COUNTERPART = ('7.1', '3.1')

TYPES_WITH_FORBIDDEN_PAYMENT = ('17.3', '17.4')

TYPES_WITH_MANDATORY_PAYMENT = tuple(inv_type for inv_type in ALL_INVOICE_TYPES if inv_type not in TYPES_WITH_FORBIDDEN_PAYMENT)

TYPES_WITH_FORBIDDEN_QUANTITY = ('2.1', '2.2', '2.3', '7.1', '8.1', '8.2')

TYPES_WITH_FORBIDDEN_CLASSIFICATION = ('3.2',)

TYPES_WITH_MANDATORY_DETAIL_TYPE = ('1.5',)

TYPES_WITH_VAT_CATEGORY_8 = ('3.1', '3.2', '8.1', '8.2', '17.3', '17.4')

COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE = (('1.1', 'category1_95'), ('3.2', 'category1_95'), ('5.1', 'category1_95'))

VALID_TAX_CATEGORY_MAP = {
    24: 1,
    13: 2,
    6: 3,
    17: 4,
    9: 5,
    4: 6,
    0: 7,
}

VALID_TAX_AMOUNTS = tuple(VALID_TAX_CATEGORY_MAP.keys())


class PreferredClassification(models.Model):
    _name = 'l10n_gr_edi.preferred_classification'
    _description = 'Preferred myDATA classification combinations for a particular product'
    _order = 'priority DESC, id DESC'

    # Inverse fields
    product_template_id = fields.Many2one(comodel_name='product.template')
    fiscal_position_id = fields.Many2one(comodel_name='account.fiscal.position')

    priority = fields.Integer(string='Priority', default=1)
    l10n_gr_edi_inv_type = fields.Selection(
        selection=INVOICE_TYPES_SELECTION,
        string='MyDATA Invoice Type',
    )
    l10n_gr_edi_cls_category = fields.Selection(
        selection=CLASSIFICATION_CATEGORY_SELECTION,
        string='MyDATA Category',
    )
    l10n_gr_edi_cls_type = fields.Selection(
        selection=CLASSIFICATION_TYPE_SELECTION,
        string='MyDATA Type',
    )

    l10n_gr_edi_available_inv_type = fields.Char(default=','.join(CLASSIFICATION_MAP.keys()))
    l10n_gr_edi_available_cls_category = fields.Char(compute='_compute_l10n_gr_edi_available_cls_category')
    l10n_gr_edi_available_cls_type = fields.Char(compute='_compute_l10n_gr_edi_available_cls_type')

    @api.onchange('l10n_gr_edi_available_cls_category')
    def _onchange_reset_cls_category(self):
        for line in self:
            line.l10n_gr_edi_cls_category = False

    @api.onchange('l10n_gr_edi_available_cls_type')
    def _onchange_reset_cls_type(self):
        for line in self:
            line.l10n_gr_edi_cls_type = False

    @api.depends('l10n_gr_edi_inv_type')
    def _compute_l10n_gr_edi_available_cls_category(self):
        for record in self:
            record.l10n_gr_edi_available_cls_category = self._get_l10n_gr_edi_available_cls_category(record.l10n_gr_edi_inv_type)

    @api.depends('l10n_gr_edi_inv_type', 'l10n_gr_edi_cls_category')
    def _compute_l10n_gr_edi_available_cls_type(self):
        for record in self:
            record.l10n_gr_edi_available_cls_type = self._get_l10n_gr_edi_available_cls_type(
                inv_type=record.l10n_gr_edi_inv_type,
                cls_category=record.l10n_gr_edi_cls_category,
            )

    ################################################################################
    # Get Classification Data Helpers
    ################################################################################

    @api.model
    def _get_l10n_gr_edi_available_cls_category(self, inv_type: str, category_type: str = '0') -> str:
        """
        Helper for getting the l10n_gr_edi_available_cls_category string value.
        :param str category_type: '0' (all, default) | '1' (income) | '2' (expense)
        """
        available_cls_category = ''

        if inv_type and CLASSIFICATION_MAP[inv_type] != 'associate':
            if category_type == '1':  # get only income categories
                available_cls_category = ','.join(category for category in CLASSIFICATION_MAP[inv_type]
                                                  if category[:9] == 'category1')
            elif category_type == '2':  # get only expense categories
                available_cls_category = ','.join(category for category in CLASSIFICATION_MAP[inv_type]
                                                  if category[:9] == 'category2')
            else:
                available_cls_category = ','.join(category for category in CLASSIFICATION_MAP[inv_type])

        return available_cls_category

    @api.model
    def _get_l10n_gr_edi_available_cls_type(self, inv_type: str, cls_category: str) -> str:
        """
        Helper for getting the l10n_gr_edi_available_cls_type string value.
        """
        available_cls_type = ''

        if (
                inv_type and
                cls_category and
                cls_category in CLASSIFICATION_MAP[inv_type]
        ):
            available_types = CLASSIFICATION_MAP[inv_type][cls_category]

            if available_types == 'all_above':
                available_types = set()
                for other_category in CLASSIFICATION_MAP[inv_type]:
                    same_category_type = other_category[:9] == cls_category[:9]  # category1* or category2*
                    contains_cls_types = isinstance(CLASSIFICATION_MAP[inv_type][other_category], tuple)
                    if same_category_type and contains_cls_types:
                        available_types.update(CLASSIFICATION_MAP[inv_type][other_category])
                available_types = tuple(available_types)

            if isinstance(available_types, tuple):
                available_cls_type = ','.join(available_types)

        return available_cls_type

    @api.model
    def _get_l10n_gr_edi_available_cls_vat(self, inv_type: str, cls_category: str) -> str:
        """
        Helper for getting the l10n_gr_edi_available_cls_vat string value.
        """
        available_cls_vat = ''

        if (
                inv_type and
                cls_category and
                cls_category in CLASSIFICATION_MAP[inv_type] and
                cls_category in CLASSIFICATION_CATEGORY_EXPENSE
        ):
            available_cls_vat = ','.join(vat[0] for vat in CLASSIFICATION_VAT_SELECTION)

        return available_cls_vat
