import json
import os
import unittest

from ua_parser import user_agent_parser
from . import compat
from .parsers import parse


iphone_ua_string = 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3'
ipad_ua_string = 'Mozilla/5.0(iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10'
galaxy_tab_ua_string = 'Mozilla/5.0 (Linux; U; Android 2.2; en-us; SCH-I800 Build/FROYO) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1'
galaxy_s3_ua_string = 'Mozilla/5.0 (Linux; U; Android 4.0.4; en-gb; GT-I9300 Build/IMM76D) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'
kindle_fire_ua_string = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us; Silk/1.1.0-80) AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16 Silk-Accelerated=true'
playbook_ua_string = 'Mozilla/5.0 (PlayBook; U; RIM Tablet OS 2.0.1; en-US) AppleWebKit/535.8+ (KHTML, like Gecko) Version/7.2.0.1 Safari/535.8+'
nexus_7_ua_string = 'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166  Safari/535.19'
windows_phone_ua_string = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0; SAMSUNG; SGH-i917)'
blackberry_torch_ua_string = 'Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; zh-TW) AppleWebKit/534.8+ (KHTML, like Gecko) Version/6.0.0.448 Mobile Safari/534.8+'
blackberry_bold_ua_string = 'BlackBerry9700/5.0.0.862 Profile/MIDP-2.1 Configuration/CLDC-1.1 VendorID/331 UNTRUSTED/1.0 3gpp-gba'
blackberry_bold_touch_ua_string = 'Mozilla/5.0 (BlackBerry; U; BlackBerry 9930; en-US) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.0.0.241 Mobile Safari/534.11+'
windows_rt_ua_string = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; ARM; Trident/6.0)'
j2me_opera_ua_string = 'Opera/9.80 (J2ME/MIDP; Opera Mini/9.80 (J2ME/22.478; U; en) Presto/2.5.25 Version/10.54'
ie_ua_string = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)'
ie_touch_ua_string = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0; Touch)'
mac_safari_ua_string = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2'
windows_ie_ua_string = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'
ubuntu_firefox_ua_string = 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1'
google_bot_ua_string = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
nokia_n97_ua_string = 'Mozilla/5.0 (SymbianOS/9.4; Series60/5.0 NokiaN97-1/12.0.024; Profile/MIDP-2.1 Configuration/CLDC-1.1; en-us) AppleWebKit/525 (KHTML, like Gecko) BrowserNG/7.1.12344'
android_firefox_aurora_ua_string = 'Mozilla/5.0 (Android; Mobile; rv:27.0) Gecko/27.0 Firefox/27.0'
thunderbird_ua_string = 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Thunderbird/38.2.0 Lightning/4.0.2'
outlook_usa_string = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/6.0; Microsoft Outlook 15.0.4420)'
chromebook_ua_string = 'Mozilla/5.0 (X11; CrOS i686 0.12.433) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.77 Safari/534.30'

iphone_ua = parse(iphone_ua_string)
ipad_ua = parse(ipad_ua_string)
galaxy_tab = parse(galaxy_tab_ua_string)
galaxy_s3_ua = parse(galaxy_s3_ua_string)
kindle_fire_ua = parse(kindle_fire_ua_string)
playbook_ua = parse(playbook_ua_string)
nexus_7_ua = parse(nexus_7_ua_string)
windows_phone_ua = parse(windows_phone_ua_string)
windows_rt_ua = parse(windows_rt_ua_string)
blackberry_torch_ua = parse(blackberry_torch_ua_string)
blackberry_bold_ua = parse(blackberry_bold_ua_string)
blackberry_bold_touch_ua = parse(blackberry_bold_touch_ua_string)
j2me_opera_ua = parse(j2me_opera_ua_string)
ie_ua = parse(ie_ua_string)
ie_touch_ua = parse(ie_touch_ua_string)
mac_safari_ua = parse(mac_safari_ua_string)
windows_ie_ua = parse(windows_ie_ua_string)
ubuntu_firefox_ua = parse(ubuntu_firefox_ua_string)
google_bot_ua = parse(google_bot_ua_string)
nokia_n97_ua = parse(nokia_n97_ua_string)
android_firefox_aurora_ua = parse(android_firefox_aurora_ua_string)
thunderbird_ua = parse(thunderbird_ua_string)
outlook_ua = parse(outlook_usa_string)
chromebook_ua = parse(chromebook_ua_string)


class UserAgentsTest(unittest.TestCase):

    def test_user_agent_object_assignments(self):
        ua_dict = user_agent_parser.Parse(devices['iphone']['ua_string'])
        iphone_ua = devices['iphone']['user_agent']

        # Ensure browser attributes are assigned correctly
        self.assertEqual(iphone_ua.browser.family,
                         ua_dict['user_agent']['family'])
        self.assertEqual(
            iphone_ua.browser.version,
            (int(ua_dict['user_agent']['major']),
             int(ua_dict['user_agent']['minor']))
        )

        # Ensure os attributes are assigned correctly
        self.assertEqual(iphone_ua.os.family, ua_dict['os']['family'])
        self.assertEqual(
            iphone_ua.os.version,
            (int(ua_dict['os']['major']), int(ua_dict['os']['minor']))
        )

        # Ensure device attributes are assigned correctly
        self.assertEqual(iphone_ua.device.family,
                         ua_dict['device']['family'])

    def test_is_tablet_property(self):
        self.assertFalse(iphone_ua.is_tablet)
        self.assertFalse(galaxy_s3_ua.is_tablet)
        self.assertFalse(blackberry_torch_ua.is_tablet)
        self.assertFalse(blackberry_bold_ua.is_tablet)
        self.assertFalse(windows_phone_ua.is_tablet)
        self.assertFalse(ie_ua.is_tablet)
        self.assertFalse(ie_touch_ua.is_tablet)
        self.assertFalse(mac_safari_ua.is_tablet)
        self.assertFalse(windows_ie_ua.is_tablet)
        self.assertFalse(ubuntu_firefox_ua.is_tablet)
        self.assertFalse(j2me_opera_ua.is_tablet)
        self.assertFalse(google_bot_ua.is_tablet)
        self.assertFalse(nokia_n97_ua.is_tablet)
        self.assertTrue(windows_rt_ua.is_tablet)
        self.assertTrue(ipad_ua.is_tablet)
        self.assertTrue(playbook_ua.is_tablet)
        self.assertTrue(kindle_fire_ua.is_tablet)
        self.assertTrue(nexus_7_ua.is_tablet)
        self.assertFalse(android_firefox_aurora_ua.is_tablet)

    def test_is_mobile_property(self):
        self.assertTrue(iphone_ua.is_mobile)
        self.assertTrue(galaxy_s3_ua.is_mobile)
        self.assertTrue(blackberry_torch_ua.is_mobile)
        self.assertTrue(blackberry_bold_ua.is_mobile)
        self.assertTrue(windows_phone_ua.is_mobile)
        self.assertTrue(j2me_opera_ua.is_mobile)
        self.assertTrue(nokia_n97_ua.is_mobile)
        self.assertFalse(windows_rt_ua.is_mobile)
        self.assertFalse(ipad_ua.is_mobile)
        self.assertFalse(playbook_ua.is_mobile)
        self.assertFalse(kindle_fire_ua.is_mobile)
        self.assertFalse(nexus_7_ua.is_mobile)
        self.assertFalse(ie_ua.is_mobile)
        self.assertFalse(ie_touch_ua.is_mobile)
        self.assertFalse(mac_safari_ua.is_mobile)
        self.assertFalse(windows_ie_ua.is_mobile)
        self.assertFalse(ubuntu_firefox_ua.is_mobile)
        self.assertFalse(google_bot_ua.is_mobile)
        self.assertTrue(android_firefox_aurora_ua.is_mobile)

    def test_is_touch_property(self):
        self.assertTrue(iphone_ua.is_touch_capable)
        self.assertTrue(galaxy_s3_ua.is_touch_capable)
        self.assertTrue(ipad_ua.is_touch_capable)
        self.assertTrue(playbook_ua.is_touch_capable)
        self.assertTrue(kindle_fire_ua.is_touch_capable)
        self.assertTrue(nexus_7_ua.is_touch_capable)
        self.assertTrue(windows_phone_ua.is_touch_capable)
        self.assertTrue(ie_touch_ua.is_touch_capable)
        self.assertTrue(blackberry_bold_touch_ua.is_mobile)
        self.assertTrue(blackberry_torch_ua.is_mobile)
        self.assertFalse(j2me_opera_ua.is_touch_capable)
        self.assertFalse(ie_ua.is_touch_capable)
        self.assertFalse(blackberry_bold_ua.is_touch_capable)
        self.assertFalse(mac_safari_ua.is_touch_capable)
        self.assertFalse(windows_ie_ua.is_touch_capable)
        self.assertFalse(ubuntu_firefox_ua.is_touch_capable)
        self.assertFalse(google_bot_ua.is_touch_capable)
        self.assertFalse(nokia_n97_ua.is_touch_capable)
        self.assertTrue(android_firefox_aurora_ua.is_touch_capable)

    def test_is_pc(self):
        self.assertFalse(iphone_ua.is_pc)
        self.assertFalse(galaxy_s3_ua.is_pc)
        self.assertFalse(ipad_ua.is_pc)
        self.assertFalse(playbook_ua.is_pc)
        self.assertFalse(kindle_fire_ua.is_pc)
        self.assertFalse(nexus_7_ua.is_pc)
        self.assertFalse(windows_phone_ua.is_pc)
        self.assertFalse(blackberry_bold_touch_ua.is_pc)
        self.assertFalse(blackberry_torch_ua.is_pc)
        self.assertFalse(blackberry_bold_ua.is_pc)
        self.assertFalse(j2me_opera_ua.is_pc)
        self.assertFalse(google_bot_ua.is_pc)
        self.assertFalse(nokia_n97_ua.is_pc)
        self.assertTrue(mac_safari_ua.is_pc)
        self.assertTrue(windows_ie_ua.is_pc)
        self.assertTrue(ubuntu_firefox_ua.is_pc)
        self.assertTrue(ie_touch_ua.is_pc)
        self.assertTrue(ie_ua.is_pc)
        self.assertFalse(android_firefox_aurora_ua.is_pc)
        self.assertTrue(chromebook_ua.is_pc)

    def test_is_bot(self):
        self.assertTrue(google_bot_ua.is_bot)
        self.assertFalse(iphone_ua.is_bot)
        self.assertFalse(galaxy_s3_ua.is_bot)
        self.assertFalse(ipad_ua.is_bot)
        self.assertFalse(playbook_ua.is_bot)
        self.assertFalse(kindle_fire_ua.is_bot)
        self.assertFalse(nexus_7_ua.is_bot)
        self.assertFalse(windows_phone_ua.is_bot)
        self.assertFalse(blackberry_bold_touch_ua.is_bot)
        self.assertFalse(blackberry_torch_ua.is_bot)
        self.assertFalse(blackberry_bold_ua.is_bot)
        self.assertFalse(j2me_opera_ua.is_bot)
        self.assertFalse(mac_safari_ua.is_bot)
        self.assertFalse(windows_ie_ua.is_bot)
        self.assertFalse(ubuntu_firefox_ua.is_bot)
        self.assertFalse(ie_touch_ua.is_bot)
        self.assertFalse(ie_ua.is_bot)
        self.assertFalse(nokia_n97_ua.is_bot)
        self.assertFalse(android_firefox_aurora_ua.is_bot)

    def test_is_email_client(self):
        self.assertTrue(thunderbird_ua.is_email_client)
        self.assertTrue(outlook_ua.is_email_client)
        self.assertFalse(playbook_ua.is_email_client)
        self.assertFalse(kindle_fire_ua.is_email_client)
        self.assertFalse(nexus_7_ua.is_email_client)
        self.assertFalse(windows_phone_ua.is_email_client)
        self.assertFalse(blackberry_bold_touch_ua.is_email_client)
        self.assertFalse(blackberry_torch_ua.is_email_client)
        self.assertFalse(blackberry_bold_ua.is_email_client)
        self.assertFalse(j2me_opera_ua.is_email_client)
        self.assertFalse(mac_safari_ua.is_email_client)
        self.assertFalse(windows_ie_ua.is_email_client)
        self.assertFalse(ubuntu_firefox_ua.is_email_client)
        self.assertFalse(ie_touch_ua.is_email_client)
        self.assertFalse(ie_ua.is_email_client)
        self.assertFalse(nokia_n97_ua.is_email_client)
        self.assertFalse(android_firefox_aurora_ua.is_email_client)


    def test_strings(self):
        self.assertEqual(str(iphone_ua), "iPhone / iOS 5.1 / Mobile Safari 5.1")
        self.assertEqual(str(ipad_ua), "iPad / iOS 3.2 / Mobile Safari 4.0.4")
        self.assertEqual(str(galaxy_tab), "Samsung SCH-I800 / Android 2.2 / Android 2.2")
        self.assertEqual(str(galaxy_s3_ua), "Samsung GT-I9300 / Android 4.0.4 / Android 4.0.4")
        self.assertEqual(str(kindle_fire_ua), "Kindle / Android / Amazon Silk 1.1.0-80")
        self.assertEqual(str(playbook_ua), "BlackBerry Playbook / BlackBerry Tablet OS 2.0.1 / BlackBerry WebKit 2.0.1")
        self.assertEqual(str(nexus_7_ua), "Asus Nexus 7 / Android 4.1.1 / Chrome 18.0.1025")
        self.assertEqual(str(windows_phone_ua), "Samsung SGH-i917 / Windows Phone 7.5 / IE Mobile 9.0")
        self.assertEqual(str(windows_rt_ua), "PC / Windows RT / IE 10.0")
        self.assertEqual(str(blackberry_torch_ua), "BlackBerry 9800 / BlackBerry OS 6.0.0 / BlackBerry WebKit 6.0.0")
        self.assertEqual(str(blackberry_bold_ua), "BlackBerry 9700 / BlackBerry OS 5.0.0 / BlackBerry 9700")
        self.assertEqual(str(blackberry_bold_touch_ua), "BlackBerry 9930 / BlackBerry OS 7.0.0 / BlackBerry WebKit 7.0.0")
        self.assertEqual(str(j2me_opera_ua), "Generic Feature Phone / Other / Opera Mini 9.80")
        self.assertEqual(str(ie_ua), "PC / Windows 8 / IE 10.0")
        self.assertEqual(str(ie_touch_ua), "PC / Windows 8 / IE 10.0")
        self.assertEqual(str(mac_safari_ua), "PC / Mac OS X 10.6.8 / WebKit Nightly 537.13")
        self.assertEqual(str(windows_ie_ua), "PC / Windows 7 / IE 9.0")
        self.assertEqual(str(ubuntu_firefox_ua), "PC / Ubuntu / Firefox 15.0.1")
        self.assertEqual(str(google_bot_ua), "Spider / Other / Googlebot 2.1")
        self.assertEqual(str(nokia_n97_ua), "Nokia N97 / Symbian OS 9.4 / Nokia Browser 7.1.12344")
        self.assertEqual(str(android_firefox_aurora_ua), "Generic Smartphone / Android / Firefox Mobile 27.0")

    def test_unicode_strings(self):
        try:
            # Python 2
            unicode_ua_str = unicode(devices['iphone']['user_agent'])
            self.assertEqual(unicode_ua_str,
                             u"iPhone / iOS 5.1 / Mobile Safari 5.1")
            self.assertTrue(isinstance(unicode_ua_str, unicode))
        except NameError:
            # Python 3
            unicode_ua_str = str(devices['iphone']['user_agent'])
            self.assertEqual(unicode_ua_str,
                             "iPhone / iOS 5.1 / Mobile Safari 5.1")


with open(os.path.join(os.path.dirname(__file__), 'devices.json')) as f:
    devices = json.load(f)


def test_wrapper(items):
    def test_func(self):
        attrs = ('is_bot', 'is_mobile',
                 'is_pc', 'is_tablet', 'is_touch_capable')
        for attr in attrs:
            self.assertEqual(
                getattr(items['user_agent'], attr), items[attr], msg=attr)
        # Temporarily commenting this out since UserAgent.device
        # may return different string depending ua-parser version
        # self.assertEqual(str(items['user_agent']), items['str'])
    return test_func

for device, items in compat.iteritems(devices):
    items['user_agent'] = parse(items['ua_string'])
    setattr(UserAgentsTest, 'test_' + device, test_wrapper(items))
