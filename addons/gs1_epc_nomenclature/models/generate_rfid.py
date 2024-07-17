# Set constants.
BARCODE_POPULATE = [
    '6016478556509', '6016478556493', '6016478556523', '6016478559982',
    '6016478559999', '2300001000008', '6016478556417', '6016478556424',
    '6016478556431', '6016478556349', '6016478556332', '6016478556400',
    '6016478556318', '6016478556677', '6016478556530', '6016478556370',
    '6016478556448', '6016478556387', '6016478556516', '6016478556486',
    '6016478556455', '6016478556356'
]
BARCODE_PRODUCT = [
    'Large Cabinet', 'Pedal Bin', 'Cabinet with doors - Serial (helpdesk_stock needed)', 'Customized Cabinet (Metric)',
    'Customized Cabinet (USA)', 'Desk Organizer', 'Customizable Desk (Steel, White)', 'Customizable Desk (Steel, Black)',
    'Customizable Desk (Aluminium, White)', 'Office Chair Black', 'Individual Workplace', 'Corner Desk Left Sit',
    'Cable Management Box - Lot (FURN_5555)', 'Cable Management Box - Lot (FURN_5800)', 'Acoustic Bloc Screens (Wood)', 'Large Meeting Table',
    'Desk Combination', 'Desk Stand with Screen', 'Four Person Desk', 'Drawer',
    'Drawer Black', 'Three-Seat Sofa'
]
RFID_TAG_STRUCT = "urn:epc:tag:sgtin-96:1.{company}.{indicator}{product}.{serial}"
RFIDS = {}


random_sn = True
start_sn = 0

number_of_rfid_by_products = 20

# Generates the RFID.
for product, barcode in zip(BARCODE_PRODUCT, BARCODE_POPULATE):
    serial = 0  # random.randint(start_sn, start_sn+1000) if random_sn else start_sn
    company = barcode[:-7]
    barcode = barcode[-7:-1]
    RFIDS[product] = []
    for i in range(number_of_rfid_by_products):
        RFIDS[product].append(RFID_TAG_STRUCT.format(indicator=0, company=int(company), product=int(barcode), serial=serial))
        serial += 1

message = []
for product in RFIDS:
    vals = [{'uri_tag': uri} for uri in product]
    schemes = model.create(vals)
    message.append(f"{product},")
    message.extend(f"{scheme.uri_tag},{scheme.hex_value}" for scheme in schemes)

log('\n'.join(message))
