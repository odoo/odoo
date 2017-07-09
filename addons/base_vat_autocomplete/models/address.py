import stdnum.eu.vat
import re

vats = [
    'NL819064865B01', 'PT508968453', 'FR68478044860', 'RO1104239', 'FR23751753237', 
    'FR52502863889', 'CO9003744754', 'BE0828426223', 'IT02372990214', 'FR68390149474']
vats = [
    'GB137776084', 'BR00496149164', 'FR03437988074', 'IT02807961202', 'IT04229890233', 
    'IT00866500325', 'BE0546704074', 'DE115683763', 'DE 119886186', 'ESA28809416', 
    'FR95810340679', 'ESB55134449', 'NL819705056B01', 'IN29971188650', 'VN0106023568', 
    'FI21974007', 'LU23628781', 'BE0839083157', 'FR60483249942', 'BE0822741231', 'ESB82833336', 
    'HR32906314355', 'BE 0898.017.387', 'BE0455699070', 'BE0824928481', 'ES71220112Z', 
    'CC 595, 10', 'BE 0819967031', 'ATU70795516']
vats = [
    'GB970046431', 'FR13535248975', 'DE259980759', 'DE180835425', 'FR85499284503', 
    'AD0767507', 'LU14363073', 'BE0543739834', 'CO 900 688 509 4', 'DE298931102', 'BE0809796085', 
    'BE 0834 334 315', 'NO916867921', 'LU28084247', 'IT04383110659', 'Mt 21313106', 'DE286548629', 
    'FR 72 538601444', 'BE0808427791', 'ESB87530432']

def _check_city(lines, country='BE'):
    if country=='GB':
        ukzip = '[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}'
        if re.match(ukzip, lines[-1]):
            cp = lines.pop()
            city = lines.pop()
            return (cp, city)
    else:
        result = re.match('((?:L-|AT-)?[0-9\-]+) (.+)', lines[-1])
        if result:
            lines.pop()
            return (result.group(1), result.group(2))
    return False

for vat in vats:
    try:
        result = stdnum.eu.vat.check_vies(vat)
    except:
        continue
    if not result['valid']: continue
    if result['address'] == '---': continue

    print '-'*50
    print result["address"]
    lines = filter(None, result['address'].split("\n"))
    street = lines.pop(0)
    cp = city = street2 = ''
    if len(lines)>0:
        res = _check_city(lines, result['countryCode'])
        if res:
            cp = res[0]
            city = res[1]
    if len(lines)>0:
        street2 = lines.pop(0)
    print """street: %s \nstreet2: %s \nzip:%s \ncity:%s""" % (street, street2, cp, city)
    print





