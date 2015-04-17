# -*- coding: utf-8 -*-

from SOAPpy import SOAPProxy, WSDL

url = 'https://ws1.mercurydev.net/ws/ws.asmx'
namespace   = 'http://www.mercurypay.com'
soapaction  = 'http://www.mercurypay.com/CreditTransaction'
password    = 'xyz'

message = """<TStream>
<Transaction>
<MerchantID>595901</MerchantID>
<OperatorID>test</OperatorID>
<TranType>Credit</TranType>
<TranCode>Sale</TranCode>
<InvoiceNo>10</InvoiceNo>
<Memo>Odoo</Memo>
<Account>
<AccountSource>Swiped</AccountSource>
<EncryptedBlock>E0164DDCA72EEA4BA62FFEA4D4DDF0DA76F878D41EF09AFDC1938B29697A3E9CADA9B8DA9FA27678</EncryptedBlock>
<EncryptedKey>9012090B29C0CE000140</EncryptedKey>
<EncryptedFormat>MagneSafe</EncryptedFormat>
</Account>
<Amount>
<Purchase>1.05</Purchase>
</Amount>
</Transaction>
</TStream>"""

server = SOAPProxy(url, namespace, soapaction)

# if you want to see the SOAP message exchanged
# uncomment the two following lines

server.config.dumpSOAPOut = 1
server.config.dumpSOAPIn  = 1
server.config.debug       = 1

# we see here how to specify the parameter name in the call
# (String_1)

print server.CreditTransaction(tran=message, pwd=password)
