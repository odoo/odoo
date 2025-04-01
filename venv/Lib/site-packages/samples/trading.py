# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
import datetime
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading


def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")

    (opts, args) = parser.parse_args()
    return opts, args


def run(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid)

        api.execute('GetCharities', {'CharityID': 3897})
        dump(api)
        print(api.response.reply.Charity.Name)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def feedback(opts):
    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        api.execute('GetFeedback', {'UserID': 'tim0th3us'})
        dump(api)

        if int(api.response.reply.FeedbackScore) > 50:
            print("Doing good!")
        else:
            print("Sell more, buy more..")

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def getTokenStatus(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        api.execute('GetTokenStatus')
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def verifyAddItem(opts):
    """http://www.utilities-online.info/xmltojson/#.UXli2it4avc
    """

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        myitem = {
            "Item": {
                "Title": "Harry Potter and the Philosopher's Stone",
                "Description": "This is the first book in the Harry Potter series. In excellent condition!",
                "PrimaryCategory": {"CategoryID": "377"},
                "StartPrice": "1.0",
                "CategoryMappingAllowed": "true",
                "Country": "US",
                "ConditionID": "3000",
                "Currency": "USD",
                "DispatchTimeMax": "3",
                "ListingDuration": "Days_7",
                "ListingType": "Chinese",
                "PaymentMethods": "PayPal",
                "PayPalEmailAddress": "tkeefdddder@gmail.com",
                "PictureDetails": {"PictureURL": "http://i1.sandbox.ebayimg.com/03/i/00/30/07/20_1.JPG?set_id=8800005007"},
                "PostalCode": "95125",
                "Quantity": "1",
                "ReturnPolicy": {
                    "ReturnsAcceptedOption": "ReturnsAccepted",
                    "RefundOption": "MoneyBack",
                    "ReturnsWithinOption": "Days_30",
                    "Description": "If you are not satisfied, return the book for refund.",
                    "ShippingCostPaidByOption": "Buyer"
                },
                "ShippingDetails": {
                    "ShippingType": "Flat",
                    "ShippingServiceOptions": {
                        "ShippingServicePriority": "1",
                        "ShippingService": "USPSMedia",
                        "ShippingServiceCost": "2.50"
                    }
                },
                "Site": "US"
            }
        }

        api.execute('VerifyAddItem', myitem)
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def verifyAddItemErrorCodes(opts):
    """http://www.utilities-online.info/xmltojson/#.UXli2it4avc
    """

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        myitem = {
            "Item": {
                "Title": "Harry Potter and the Philosopher's Stone",
                "Description": "This is the first book in the Harry Potter series. In excellent condition!",
                "PrimaryCategory": {"CategoryID": "377aaaaaa"},
                "StartPrice": "1.0",
                "CategoryMappingAllowed": "true",
                "Country": "US",
                "ConditionID": "3000",
                "Currency": "USD",
                "DispatchTimeMax": "3",
                "ListingDuration": "Days_7",
                "ListingType": "Chinese",
                "PaymentMethods": "PayPal",
                "PayPalEmailAddress": "tkeefdddder@gmail.com",
                "PictureDetails": {"PictureURL": "http://i1.sandbox.ebayimg.com/03/i/00/30/07/20_1.JPG?set_id=8800005007"},
                "PostalCode": "95125",
                "Quantity": "1",
                "ReturnPolicy": {
                    "ReturnsAcceptedOption": "ReturnsAccepted",
                    "RefundOption": "MoneyBack",
                    "ReturnsWithinOption": "Days_30",
                    "Description": "If you are not satisfied, return the book for refund.",
                    "ShippingCostPaidByOption": "Buyer"
                },
                "ShippingDetails": {
                    "ShippingType": "Flat",
                    "ShippingServiceOptions": {
                        "ShippingServicePriority": "1",
                        "ShippingService": "USPSMedia",
                        "ShippingServiceCost": "2.50"
                    }
                },
                "Site": "US"
            }
        }

        motors_item = {
            'Item': {
                'Category': '101',
                'Title': 'My Title',
                'ItemCompatibilityList': {
                    'Compatibility': [
                        {
                            'CompatibilityNotes': 'Fits for all trims and engines.',
                            'NameValueList': [
                                {'Name': 'Year', 'Value': '2001'},
                                {'Name': 'Make', 'Value': 'Honda'},
                                {'Name': 'Model', 'Value': 'Accord'}
                            ]
                         },
                    ]
                }
            }
        }

        api.execute('VerifyAddItem', myitem)

    except ConnectionError as e:
        # traverse the DOM to look for error codes
        for node in api.response.dom().findall('ErrorCode'):
            print("error code: %s" % node.text)

        # check for invalid data - error code 37
        if 37 in api.response_codes():
            print("Invalid data in request")

        print(e)
        print(e.response.dict())


def uploadPicture(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True)

        pictureData = {
            "WarningLevel": "High",
            "ExternalPictureURL": "http://developer.ebay.com/DevZone/XML/docs/images/hp_book_image.jpg",
            "PictureName": "WorldLeaders"
        }

        api.execute('UploadSiteHostedPictures', pictureData)
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def uploadPictureFromFilesystem(opts, filepath):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True)

        # pass in an open file
        # the Requests module will close the file
        files = {'file': ('EbayImage', open(filepath, 'rb'))}

        pictureData = {
            "WarningLevel": "High",
            "PictureName": "WorldLeaders"
        }

        api.execute('UploadSiteHostedPictures', pictureData, files=files)
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def memberMessages(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True)

        now = datetime.datetime.now()

        memberData = {
            "WarningLevel": "High",
            "MailMessageType": "All",
            # "MessageStatus": "Unanswered",
            "StartCreationTime": now - datetime.timedelta(days=60),
            "EndCreationTime": now,
            "Pagination": {
                "EntriesPerPage": "5",
                "PageNumber": "1"
            }
        }

        api.execute('GetMemberMessages', memberData)

        dump(api)

        if api.response.reply.has_key('MemberMessage'):
            messages = api.response.reply.MemberMessage.MemberMessageExchange

            if type(messages) != list:
                messages = [messages]

            for m in messages:
                print("%s: %s" % (m.CreationDate, m.Question.Subject[:50]))

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def getUser(opts):
    try:

        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20, siteid='101')

        api.execute('GetUser', {'UserID': 'sallyma789'})
        dump(api, full=False)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def getOrders(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20)

        api.execute('GetOrders', {'NumberOfDays': 30})
        dump(api, full=False)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def categories(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20, siteid='0')

        callData = {
            'DetailLevel': 'ReturnAll',
            'CategorySiteID': 101,
            'LevelLimit': 4,
        }

        api.execute('GetCategories', callData)
        dump(api, full=False)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())

'''
api = trading(domain='api.sandbox.ebay.com')
api.execute('GetCategories', {
    'DetailLevel': 'ReturnAll',
    'CategorySiteID': 101,
    'LevelLimit': 4,
})
'''

if __name__ == "__main__":
    (opts, args) = init_options()

    print("Trading API Samples for version %s" % ebaysdk.get_version())

    """
    run(opts)
    feedback(opts)
    verifyAddItem(opts)
    getTokenStatus(opts)
    verifyAddItemErrorCodes(opts)
    uploadPicture(opts)
    uploadPictureFromFilesystem(opts, ("%s/test_image.jpg" % os.path.dirname(__file__)))
    memberMessages(opts)
    """
    categories(opts)
    
    #getUser(opts)
    # getOrders(opts)
