import os
import sys

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from ebaysdk.utils import dict2xml

dict1 = {'a': 'b'}

assert(dict2xml(dict1) == '<a>b</a>')

''' dict2 XML Output
<tag attr2="attr2value" site="US">222</tag>
'''

dict2 = {
    'tag': {
        '#text': 222,
        '@attrs': {'site': 'US', 'attr2': 'attr2value'}
    }
}

assert(dict2xml(dict2) == '<tag attr2="attr2value" site="US">222</tag>')

''' dict3 XML Output
<itemFilter>
    <name>Condition</name>
    <value>Used</value>
</itemFilter>
<itemFilter>
    <name>LocatedIn</name>
    <value>GB</value>
</itemFilter>
<itemFilter>
    <name>More</name>
    <value>more</value>
</itemFilter>
'''

dict3 = {
    'itemFilter': [
        {'name': 'Condition', 'value': 'Used'},
        {'name': 'LocatedIn', 'value': 'GB'},
        {'name': 'More', 'value': 'more'},
    ]
}

assert(dict2xml(dict3) == '<itemFilter><name>Condition</name><value>Used</value></itemFilter><itemFilter><name>LocatedIn</name><value>GB</value></itemFilter><itemFilter><name>More</name><value>more</value></itemFilter>')

''' dict4 XML Output
<tag1 attr2="attr2value" site="US">
    <tag2>tag2 value</tag2>
</tag1>
'''

dict4 = {
    'tag1': {
        '#text': {'tag2': 'tag2 value'},
        '@attrs': {'site': 'US', 'attr2': 'attr2value'}
    }
}

assert(dict2xml(dict4) ==
       '<tag1 attr2="attr2value" site="US"><tag2>tag2 value</tag2></tag1>')

''' dict5 XML Output
<tag1 site="US" tag1attr="myvalue">
    <tag2 tag2attr="myvalue">tag2 value</tag2>
</tag1>
'''

dict5 = {
    'tag1': {
        '#text': {'tag2': {
            '#text': 'tag2 value',
            '@attrs': {'tag2attr': 'myvalue'}
        }},
        '@attrs': {'site': 'US', 'tag1attr': 'myvalue'}
    }
}

assert(dict2xml(dict5) ==
       '<tag1 site="US" tag1attr="myvalue"><tag2 tag2attr="myvalue">tag2 value</tag2></tag1>')

''' dict6 outputSelector
<outputSelector>SellerInfo</outputSelector>
<outputSelector>GalleryInfo</outputSelector>
'''

dict6 = {
    'outputSelector': [
        'SellerInfo',
        'GalleryInfo'
    ]
}

assert(dict2xml(dict6) ==
       '<outputSelector>SellerInfo</outputSelector><outputSelector>GalleryInfo</outputSelector>')
