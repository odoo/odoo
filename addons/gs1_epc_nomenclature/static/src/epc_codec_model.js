const SCHEME_TEMPLATE = {
    0x30: {
        'name': 'SGTIN-96',
        'uri_pattern_tag': 'urn:epc:tag:sgtin-96:F.C.I.S',
        'uri_pure_tag': 'urn:epc:id:sgtin:C.I.S',
        'partition': 'sgtin',
        'fields_template': ['header', 'filter', 'partition', 'company_prefix', 'item_reference', 'serial_integer'],
        'fields_bit_count': [8, 3, 3, 0, 0, 38], // 0 is for dynamically sized fields
        'ai_list': {
            '01': null, // To 'compute'
            '21': 'serial_integer', // Simply copy
        },
    },
    0x36: {
        'name': 'SGTIN-198',
        'uri_pattern_tag': 'urn:epc:tag:sgtin-198:F.C.I.S',
        'uri_pure_tag': 'urn:epc:id:sgtin:C.I.S',
        'partition': 'sgtin',
        'fields_template': ['header', 'filter', 'partition', 'company_prefix', 'item_reference', 'serial_string'],
        'fields_bit_count': [8, 3, 3, 0, 0, 140],
        'ai_list': {
            '01': null,
            '21': 'serial_string',
        },
    },
    0x31: {
        'name': 'SSCC-96',
        'uri_pattern_tag': 'urn:epc:tag:sscc-96:F.C.S',
        'partition': 'sscc',
        'fields_template': ['header', 'filter', 'partition', 'company_prefix', 'serial_integer', 'blank'],
        'fields_bit_count': [8, 3, 3, 0, 0, 24],
        'ai_list': {
            '00': null,
        },
    },
    0x32: {
        'name': 'SGLN-96',
        'uri_pattern_tag': 'urn:epc:tag:sgln-96:F.C.L.E',
        'partition': 'sgln',
        'fields_template': ['header', 'filter', 'partition', 'company_prefix', 'location_reference', 'extension_integer'],
        'fields_bit_count': [8, 3, 3, 0, 0, 41],
        'ai_list': {
            '414': null,
            '254': 'extension_integer',
        },

    },
    0x39: {
        'name': 'SGLN-195',
        'uri_pattern_tag': 'urn:epc:tag:sgln-195:F.C.L.E',
        'partition': 'sgln',
        'fields_template': ['header', 'filter', 'partition', 'company_prefix', 'location_reference', 'extension_string'],
        'fields_bit_count': [8, 3, 3, 0, 0, 140],
        'ai_list': {
            '414': null,
            '254': 'extension_string',
        },
    },
}

const FIELD_TEMPLATE = {
    'header':{
        'name': 'EPC Header',
        'encoding': 'integer',
    },
    'filter':{
        'name': 'Filter',
        'encoding': 'integer',
        'uri_portion': 'F',
    },
    'partition':{
        'name': 'Partition',
        'encoding': 'partition_table',
    },
    'company_prefix':{
        'name': 'Company Prefix',
        'encoding': 'integer',
        'uri_portion': 'C',
    },
    'item_reference':{
        'name': 'Item Reference',
        'encoding': 'integer',
        'uri_portion': 'I',
    },
    'serial_integer':{
        'name': 'Serial (Integer)',
        'encoding': 'integer',
        'uri_portion': 'S',
    },
    'serial_string':{
        'name': 'Serial (Alphanumeric)',
        'encoding': 'string',
        'uri_portion': 'S',
    },
    'blank':{
        'name': 'Blank Filler',
        'encoding': 'blank',
    },
    'location_reference':{
        'name': 'Location Reference',
        'encoding': 'integer',
        'uri_portion': 'L',
    },
    'extension_integer':{
        'name': 'Extension (Integer)',
        'encoding': 'integer',
        'uri_portion': 'E',
    },
    'extension_string':{
        'name': 'Extension (Alphanumeric)',
        'encoding': 'string',
        'uri_portion': 'E',
    },
}

const PARTITION = {
    'sgtin': {
        0: { left_bit: 40, left_digit: 12, right_bit: 4, right_digit: 1 },
        1: { left_bit: 37, left_digit: 11, right_bit: 7, right_digit: 2 },
        2: { left_bit: 34, left_digit: 10, right_bit: 10, right_digit: 3 },
        3: { left_bit: 30, left_digit: 9, right_bit: 14, right_digit: 4 },
        4: { left_bit: 27, left_digit: 8, right_bit: 17, right_digit: 5 },
        5: { left_bit: 24, left_digit: 7, right_bit: 20, right_digit: 6 },
        6: { left_bit: 20, left_digit: 6, right_bit: 24, right_digit: 7 },
    },
    'sscc': {
        0: { left_bit: 40, left_digit: 12, right_bit: 18, right_digit: 5 },
        1: { left_bit: 37, left_digit: 11, right_bit: 21, right_digit: 6 },
        2: { left_bit: 34, left_digit: 10, right_bit: 24, right_digit: 7 },
        3: { left_bit: 30, left_digit: 9, right_bit: 28, right_digit: 8 },
        4: { left_bit: 27, left_digit: 8, right_bit: 31, right_digit: 9 },
        5: { left_bit: 24, left_digit: 7, right_bit: 34, right_digit: 10 },
        6: { left_bit: 20, left_digit: 6, right_bit: 38, right_digit: 11 },
    },
    'sgln': {
        0: { left_bit: 40, left_digit: 12, right_bit: 1, right_digit: 0 },
        1: { left_bit: 37, left_digit: 11, right_bit: 4, right_digit: 1 },
        2: { left_bit: 34, left_digit: 10, right_bit: 7, right_digit: 2 },
        3: { left_bit: 30, left_digit: 9, right_bit: 11, right_digit: 3 },
        4: { left_bit: 27, left_digit: 8, right_bit: 14, right_digit: 4 },
        5: { left_bit: 24, left_digit: 7, right_bit: 17, right_digit: 5 },
        6: { left_bit: 20, left_digit: 6, right_bit: 21, right_digit: 6 },
    },
    'grai': {
        0: { left_bit: 40, left_digit: 12, right_bit: 4, right_digit: 0 },
        1: { left_bit: 37, left_digit: 11, right_bit: 7, right_digit: 1 },
        2: { left_bit: 34, left_digit: 10, right_bit: 10, right_digit: 2 },
        3: { left_bit: 30, left_digit: 9, right_bit: 14, right_digit: 3 },
        4: { left_bit: 27, left_digit: 8, right_bit: 17, right_digit: 4 },
        5: { left_bit: 24, left_digit: 7, right_bit: 20, right_digit: 5 },
        6: { left_bit: 20, left_digit: 6, right_bit: 24, right_digit: 6 },
    },
    'giai96': {
        0: { left_bit: 40, left_digit: 12, right_bit: 42, right_digit: 13 },
        1: { left_bit: 37, left_digit: 11, right_bit: 45, right_digit: 14 },
        2: { left_bit: 34, left_digit: 10, right_bit: 48, right_digit: 15 },
        3: { left_bit: 30, left_digit: 9, right_bit: 52, right_digit: 16 },
        4: { left_bit: 27, left_digit: 8, right_bit: 55, right_digit: 17 },
        5: { left_bit: 24, left_digit: 7, right_bit: 58, right_digit: 18 },
        6: { left_bit: 20, left_digit: 6, right_bit: 62, right_digit: 19 },
    },
    'giai202': {
        0: { left_bit: 40, left_digit: 12, right_bit: 148, right_digit: 18 },
        1: { left_bit: 37, left_digit: 11, right_bit: 151, right_digit: 19 },
        2: { left_bit: 34, left_digit: 10, right_bit: 154, right_digit: 20 },
        3: { left_bit: 30, left_digit: 9, right_bit: 158, right_digit: 21 },
        4: { left_bit: 27, left_digit: 8, right_bit: 161, right_digit: 22 },
        5: { left_bit: 24, left_digit: 7, right_bit: 164, right_digit: 23 },
        6: { left_bit: 20, left_digit: 6, right_bit: 168, right_digit: 24 },
    },
    'gsrn': {
        0: { left_bit: 40, left_digit: 12, right_bit: 18, right_digit: 5 },
        1: { left_bit: 37, left_digit: 11, right_bit: 21, right_digit: 6 },
        2: { left_bit: 34, left_digit: 10, right_bit: 24, right_digit: 7 },
        3: { left_bit: 30, left_digit: 9, right_bit: 28, right_digit: 8 },
        4: { left_bit: 27, left_digit: 8, right_bit: 31, right_digit: 9 },
        5: { left_bit: 24, left_digit: 7, right_bit: 34, right_digit: 10 },
        6: { left_bit: 20, left_digit: 6, right_bit: 38, right_digit: 11 },
    },
    'gsrnp': {
        0: { left_bit: 40, left_digit: 12, right_bit: 18, right_digit: 5 },
        1: { left_bit: 37, left_digit: 11, right_bit: 21, right_digit: 6 },
        2: { left_bit: 34, left_digit: 10, right_bit: 24, right_digit: 7 },
        3: { left_bit: 30, left_digit: 9, right_bit: 28, right_digit: 8 },
        4: { left_bit: 27, left_digit: 8, right_bit: 31, right_digit: 9 },
        5: { left_bit: 24, left_digit: 7, right_bit: 34, right_digit: 10 },
        6: { left_bit: 20, left_digit: 6, right_bit: 38, right_digit: 11 },
    },
    'gdti': {
        0: { left_bit: 40, left_digit: 12, right_bit: 1, right_digit: 0 },
        1: { left_bit: 37, left_digit: 11, right_bit: 4, right_digit: 1 },
        2: { left_bit: 34, left_digit: 10, right_bit: 7, right_digit: 2 },
        3: { left_bit: 30, left_digit: 9, right_bit: 11, right_digit: 3 },
        4: { left_bit: 27, left_digit: 8, right_bit: 14, right_digit: 4 },
        5: { left_bit: 24, left_digit: 7, right_bit: 17, right_digit: 5 },
        6: { left_bit: 20, left_digit: 6, right_bit: 21, right_digit: 6 },
    },
    'cpi_96': {
        0: { left_bit: 40, left_digit: 12, right_bit: 11, right_digit: 3 },
        1: { left_bit: 37, left_digit: 11, right_bit: 14, right_digit: 4 },
        2: { left_bit: 34, left_digit: 10, right_bit: 17, right_digit: 5 },
        3: { left_bit: 30, left_digit: 9, right_bit: 21, right_digit: 6 },
        4: { left_bit: 27, left_digit: 8, right_bit: 24, right_digit: 7 },
        5: { left_bit: 24, left_digit: 7, right_bit: 27, right_digit: 8 },
        6: { left_bit: 20, left_digit: 6, right_bit: 31, right_digit: 9 },
    },
    // cpi_var special case : here, right bit is not absolute and rather define the maximum bits.
    // This is due to '6-bit Variable String Partition Table' encoding of the field.
    // That's why we should rely on right_digit instead of right_bit in the decode process for this case.
    'cpi_var': {
        0: { left_bit: 40, left_digit: 12, right_bit: 114, right_digit: 18 },
        1: { left_bit: 37, left_digit: 11, right_bit: 120, right_digit: 19 },
        2: { left_bit: 34, left_digit: 10, right_bit: 126, right_digit: 20 },
        3: { left_bit: 30, left_digit: 9, right_bit: 132, right_digit: 21 },
        4: { left_bit: 27, left_digit: 8, right_bit: 138, right_digit: 22 },
        5: { left_bit: 24, left_digit: 7, right_bit: 144, right_digit: 23 },
        6: { left_bit: 20, left_digit: 6, right_bit: 150, right_digit: 24 },
    },
    'sgcn': {
        0: { left_bit: 40, left_digit: 12, right_bit: 1, right_digit: 0 },
        1: { left_bit: 37, left_digit: 11, right_bit: 4, right_digit: 1 },
        2: { left_bit: 34, left_digit: 10, right_bit: 7, right_digit: 2 },
        3: { left_bit: 30, left_digit: 9, right_bit: 11, right_digit: 3 },
        4: { left_bit: 27, left_digit: 8, right_bit: 14, right_digit: 4 },
        5: { left_bit: 24, left_digit: 7, right_bit: 17, right_digit: 5 },
        6: { left_bit: 20, left_digit: 6, right_bit: 21, right_digit: 6 },
    },
    'itip': {
        0: { left_bit: 40, left_digit: 12, right_bit: 4, right_digit: 1 },
        1: { left_bit: 37, left_digit: 11, right_bit: 7, right_digit: 2 },
        2: { left_bit: 34, left_digit: 10, right_bit: 10, right_digit: 3 },
        3: { left_bit: 30, left_digit: 9, right_bit: 14, right_digit: 4 },
        4: { left_bit: 27, left_digit: 8, right_bit: 17, right_digit: 5 },
        5: { left_bit: 24, left_digit: 7, right_bit: 20, right_digit: 6 },
        6: { left_bit: 20, left_digit: 6, right_bit: 24, right_digit: 7 },
    },
};
