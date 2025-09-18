# The following code was copied from the original author's repository
# at https://github.com/mpcabd/python-arabic-reshaper/tree/v3.0.0/arabic_reshaper
# Version: 3.0.0

# This work is licensed under the MIT License.
# To view a copy of this license, visit https://opensource.org/licenses/MIT

# Written by Abdullah Diab (mpcabd)
# Email: mpcabd@gmail.com
# Website: http://mpcabd.xyz

# Each letter is of the format:
#
#   ('<letter>', <replacement>)
#
# And replacement is of the format:
#
#   ('<isolated>', '<initial>', '<medial>', '<final>')
#
# Where <letter> is the string to replace, and <isolated> is the replacement in
# case <letter> should be in isolated form, <initial> is the replacement in
# case <letter> should be in initial form, <medial> is the replacement in case
# <letter> should be in medial form, and <final> is the replacement in case
# <letter> should be in final form. If no replacement is specified for a form,
# then no that means the letter doesn't support this form.

UNSHAPED = 255
ISOLATED = 0
INITIAL = 1
MEDIAL = 2
FINAL = 3

TATWEEL = "\u0640"
ZWJ = "\u200d"
LETTERS_ARABIC = {
    # ARABIC LETTER HAMZA
    "\u0621": ("\ufe80", "", "", ""),
    # ARABIC LETTER ALEF WITH MADDA ABOVE
    "\u0622": ("\ufe81", "", "", "\ufe82"),
    # ARABIC LETTER ALEF WITH HAMZA ABOVE
    "\u0623": ("\ufe83", "", "", "\ufe84"),
    # ARABIC LETTER WAW WITH HAMZA ABOVE
    "\u0624": ("\ufe85", "", "", "\ufe86"),
    # ARABIC LETTER ALEF WITH HAMZA BELOW
    "\u0625": ("\ufe87", "", "", "\ufe88"),
    # ARABIC LETTER YEH WITH HAMZA ABOVE
    "\u0626": ("\ufe89", "\ufe8b", "\ufe8c", "\ufe8a"),
    # ARABIC LETTER ALEF
    "\u0627": ("\ufe8d", "", "", "\ufe8e"),
    # ARABIC LETTER BEH
    "\u0628": ("\ufe8f", "\ufe91", "\ufe92", "\ufe90"),
    # ARABIC LETTER TEH MARBUTA
    "\u0629": ("\ufe93", "", "", "\ufe94"),
    # ARABIC LETTER TEH
    "\u062a": ("\ufe95", "\ufe97", "\ufe98", "\ufe96"),
    # ARABIC LETTER THEH
    "\u062b": ("\ufe99", "\ufe9b", "\ufe9c", "\ufe9a"),
    # ARABIC LETTER JEEM
    "\u062c": ("\ufe9d", "\ufe9f", "\ufea0", "\ufe9e"),
    # ARABIC LETTER HAH
    "\u062d": ("\ufea1", "\ufea3", "\ufea4", "\ufea2"),
    # ARABIC LETTER KHAH
    "\u062e": ("\ufea5", "\ufea7", "\ufea8", "\ufea6"),
    # ARABIC LETTER DAL
    "\u062f": ("\ufea9", "", "", "\ufeaa"),
    # ARABIC LETTER THAL
    "\u0630": ("\ufeab", "", "", "\ufeac"),
    # ARABIC LETTER REH
    "\u0631": ("\ufead", "", "", "\ufeae"),
    # ARABIC LETTER ZAIN
    "\u0632": ("\ufeaf", "", "", "\ufeb0"),
    # ARABIC LETTER SEEN
    "\u0633": ("\ufeb1", "\ufeb3", "\ufeb4", "\ufeb2"),
    # ARABIC LETTER SHEEN
    "\u0634": ("\ufeb5", "\ufeb7", "\ufeb8", "\ufeb6"),
    # ARABIC LETTER SAD
    "\u0635": ("\ufeb9", "\ufebb", "\ufebc", "\ufeba"),
    # ARABIC LETTER DAD
    "\u0636": ("\ufebd", "\ufebf", "\ufec0", "\ufebe"),
    # ARABIC LETTER TAH
    "\u0637": ("\ufec1", "\ufec3", "\ufec4", "\ufec2"),
    # ARABIC LETTER ZAH
    "\u0638": ("\ufec5", "\ufec7", "\ufec8", "\ufec6"),
    # ARABIC LETTER AIN
    "\u0639": ("\ufec9", "\ufecb", "\ufecc", "\ufeca"),
    # ARABIC LETTER GHAIN
    "\u063a": ("\ufecd", "\ufecf", "\ufed0", "\ufece"),
    # ARABIC TATWEEL
    TATWEEL: (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    # ARABIC LETTER FEH
    "\u0641": ("\ufed1", "\ufed3", "\ufed4", "\ufed2"),
    # ARABIC LETTER QAF
    "\u0642": ("\ufed5", "\ufed7", "\ufed8", "\ufed6"),
    # ARABIC LETTER KAF
    "\u0643": ("\ufed9", "\ufedb", "\ufedc", "\ufeda"),
    # ARABIC LETTER LAM
    "\u0644": ("\ufedd", "\ufedf", "\ufee0", "\ufede"),
    # ARABIC LETTER MEEM
    "\u0645": ("\ufee1", "\ufee3", "\ufee4", "\ufee2"),
    # ARABIC LETTER NOON
    "\u0646": ("\ufee5", "\ufee7", "\ufee8", "\ufee6"),
    # ARABIC LETTER HEH
    "\u0647": ("\ufee9", "\ufeeb", "\ufeec", "\ufeea"),
    # ARABIC LETTER WAW
    "\u0648": ("\ufeed", "", "", "\ufeee"),
    # ARABIC LETTER (UIGHUR KAZAKH KIRGHIZ)? ALEF MAKSURA
    "\u0649": ("\ufeef", "\ufbe8", "\ufbe9", "\ufef0"),
    # ARABIC LETTER YEH
    "\u064a": ("\ufef1", "\ufef3", "\ufef4", "\ufef2"),
    # ARABIC LETTER ALEF WASLA
    "\u0671": ("\ufb50", "", "", "\ufb51"),
    # ARABIC LETTER U WITH HAMZA ABOVE
    "\u0677": ("\ufbdd", "", "", ""),
    # ARABIC LETTER TTEH
    "\u0679": ("\ufb66", "\ufb68", "\ufb69", "\ufb67"),
    # ARABIC LETTER TTEHEH
    "\u067a": ("\ufb5e", "\ufb60", "\ufb61", "\ufb5f"),
    # ARABIC LETTER BEEH
    "\u067b": ("\ufb52", "\ufb54", "\ufb55", "\ufb53"),
    # ARABIC LETTER PEH
    "\u067e": ("\ufb56", "\ufb58", "\ufb59", "\ufb57"),
    # ARABIC LETTER TEHEH
    "\u067f": ("\ufb62", "\ufb64", "\ufb65", "\ufb63"),
    # ARABIC LETTER BEHEH
    "\u0680": ("\ufb5a", "\ufb5c", "\ufb5d", "\ufb5b"),
    # ARABIC LETTER NYEH
    "\u0683": ("\ufb76", "\ufb78", "\ufb79", "\ufb77"),
    # ARABIC LETTER DYEH
    "\u0684": ("\ufb72", "\ufb74", "\ufb75", "\ufb73"),
    # ARABIC LETTER TCHEH
    "\u0686": ("\ufb7a", "\ufb7c", "\ufb7d", "\ufb7b"),
    # ARABIC LETTER TCHEHEH
    "\u0687": ("\ufb7e", "\ufb80", "\ufb81", "\ufb7f"),
    # ARABIC LETTER DDAL
    "\u0688": ("\ufb88", "", "", "\ufb89"),
    # ARABIC LETTER DAHAL
    "\u068c": ("\ufb84", "", "", "\ufb85"),
    # ARABIC LETTER DDAHAL
    "\u068d": ("\ufb82", "", "", "\ufb83"),
    # ARABIC LETTER DUL
    "\u068e": ("\ufb86", "", "", "\ufb87"),
    # ARABIC LETTER RREH
    "\u0691": ("\ufb8c", "", "", "\ufb8d"),
    # ARABIC LETTER JEH
    "\u0698": ("\ufb8a", "", "", "\ufb8b"),
    # ARABIC LETTER VEH
    "\u06a4": ("\ufb6a", "\ufb6c", "\ufb6d", "\ufb6b"),
    # ARABIC LETTER PEHEH
    "\u06a6": ("\ufb6e", "\ufb70", "\ufb71", "\ufb6f"),
    # ARABIC LETTER KEHEH
    "\u06a9": ("\ufb8e", "\ufb90", "\ufb91", "\ufb8f"),
    # ARABIC LETTER NG
    "\u06ad": ("\ufbd3", "\ufbd5", "\ufbd6", "\ufbd4"),
    # ARABIC LETTER GAF
    "\u06af": ("\ufb92", "\ufb94", "\ufb95", "\ufb93"),
    # ARABIC LETTER NGOEH
    "\u06b1": ("\ufb9a", "\ufb9c", "\ufb9d", "\ufb9b"),
    # ARABIC LETTER GUEH
    "\u06b3": ("\ufb96", "\ufb98", "\ufb99", "\ufb97"),
    # ARABIC LETTER NOON GHUNNA
    "\u06ba": ("\ufb9e", "", "", "\ufb9f"),
    # ARABIC LETTER RNOON
    "\u06bb": ("\ufba0", "\ufba2", "\ufba3", "\ufba1"),
    # ARABIC LETTER HEH DOACHASHMEE
    "\u06be": ("\ufbaa", "\ufbac", "\ufbad", "\ufbab"),
    # ARABIC LETTER HEH WITH YEH ABOVE
    "\u06c0": ("\ufba4", "", "", "\ufba5"),
    # ARABIC LETTER HEH GOAL
    "\u06c1": ("\ufba6", "\ufba8", "\ufba9", "\ufba7"),
    # ARABIC LETTER KIRGHIZ OE
    "\u06c5": ("\ufbe0", "", "", "\ufbe1"),
    # ARABIC LETTER OE
    "\u06c6": ("\ufbd9", "", "", "\ufbda"),
    # ARABIC LETTER U
    "\u06c7": ("\ufbd7", "", "", "\ufbd8"),
    # ARABIC LETTER YU
    "\u06c8": ("\ufbdb", "", "", "\ufbdc"),
    # ARABIC LETTER KIRGHIZ YU
    "\u06c9": ("\ufbe2", "", "", "\ufbe3"),
    # ARABIC LETTER VE
    "\u06cb": ("\ufbde", "", "", "\ufbdf"),
    # ARABIC LETTER FARSI YEH
    "\u06cc": ("\ufbfc", "\ufbfe", "\ufbff", "\ufbfd"),
    # ARABIC LETTER E
    "\u06d0": ("\ufbe4", "\ufbe6", "\ufbe7", "\ufbe5"),
    # ARABIC LETTER YEH BARREE
    "\u06d2": ("\ufbae", "", "", "\ufbaf"),
    # ARABIC LETTER YEH BARREE WITH HAMZA ABOVE
    "\u06d3": ("\ufbb0", "", "", "\ufbb1"),
    # ZWJ
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}

LETTERS_ARABIC_V2 = {
    # ARABIC LETTER HAMZA
    "\u0621": ("\ufe80", "", "", ""),
    # ARABIC LETTER ALEF WITH MADDA ABOVE
    "\u0622": ("\u0622", "", "", "\ufe82"),
    # ARABIC LETTER ALEF WITH HAMZA ABOVE
    "\u0623": ("\u0623", "", "", "\ufe84"),
    # ARABIC LETTER WAW WITH HAMZA ABOVE
    "\u0624": ("\u0624", "", "", "\ufe86"),
    # ARABIC LETTER ALEF WITH HAMZA BELOW
    "\u0625": ("\u0625", "", "", "\ufe88"),
    # ARABIC LETTER YEH WITH HAMZA ABOVE
    "\u0626": ("\u0626", "\ufe8b", "\ufe8c", "\ufe8a"),
    # ARABIC LETTER ALEF
    "\u0627": ("\u0627", "", "", "\ufe8e"),
    # ARABIC LETTER BEH
    "\u0628": ("\u0628", "\ufe91", "\ufe92", "\ufe90"),
    # ARABIC LETTER TEH MARBUTA
    "\u0629": ("\u0629", "", "", "\ufe94"),
    # ARABIC LETTER TEH
    "\u062a": ("\u062a", "\ufe97", "\ufe98", "\ufe96"),
    # ARABIC LETTER THEH
    "\u062b": ("\u062b", "\ufe9b", "\ufe9c", "\ufe9a"),
    # ARABIC LETTER JEEM
    "\u062c": ("\u062c", "\ufe9f", "\ufea0", "\ufe9e"),
    # ARABIC LETTER HAH
    "\u062d": ("\ufea1", "\ufea3", "\ufea4", "\ufea2"),
    # ARABIC LETTER KHAH
    "\u062e": ("\u062e", "\ufea7", "\ufea8", "\ufea6"),
    # ARABIC LETTER DAL
    "\u062f": ("\u062f", "", "", "\ufeaa"),
    # ARABIC LETTER THAL
    "\u0630": ("\u0630", "", "", "\ufeac"),
    # ARABIC LETTER REH
    "\u0631": ("\u0631", "", "", "\ufeae"),
    # ARABIC LETTER ZAIN
    "\u0632": ("\u0632", "", "", "\ufeb0"),
    # ARABIC LETTER SEEN
    "\u0633": ("\u0633", "\ufeb3", "\ufeb4", "\ufeb2"),
    # ARABIC LETTER SHEEN
    "\u0634": ("\u0634", "\ufeb7", "\ufeb8", "\ufeb6"),
    # ARABIC LETTER SAD
    "\u0635": ("\u0635", "\ufebb", "\ufebc", "\ufeba"),
    # ARABIC LETTER DAD
    "\u0636": ("\u0636", "\ufebf", "\ufec0", "\ufebe"),
    # ARABIC LETTER TAH
    "\u0637": ("\u0637", "\ufec3", "\ufec4", "\ufec2"),
    # ARABIC LETTER ZAH
    "\u0638": ("\u0638", "\ufec7", "\ufec8", "\ufec6"),
    # ARABIC LETTER AIN
    "\u0639": ("\u0639", "\ufecb", "\ufecc", "\ufeca"),
    # ARABIC LETTER GHAIN
    "\u063a": ("\u063a", "\ufecf", "\ufed0", "\ufece"),
    # ARABIC TATWEEL
    TATWEEL: (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    # ARABIC LETTER FEH
    "\u0641": ("\u0641", "\ufed3", "\ufed4", "\ufed2"),
    # ARABIC LETTER QAF
    "\u0642": ("\u0642", "\ufed7", "\ufed8", "\ufed6"),
    # ARABIC LETTER KAF
    "\u0643": ("\u0643", "\ufedb", "\ufedc", "\ufeda"),
    # ARABIC LETTER LAM
    "\u0644": ("\u0644", "\ufedf", "\ufee0", "\ufede"),
    # ARABIC LETTER MEEM
    "\u0645": ("\u0645", "\ufee3", "\ufee4", "\ufee2"),
    # ARABIC LETTER NOON
    "\u0646": ("\u0646", "\ufee7", "\ufee8", "\ufee6"),
    # ARABIC LETTER HEH
    "\u0647": ("\u0647", "\ufeeb", "\ufeec", "\ufeea"),
    # ARABIC LETTER WAW
    "\u0648": ("\u0648", "", "", "\ufeee"),
    # ARABIC LETTER (UIGHUR KAZAKH KIRGHIZ)? ALEF MAKSURA
    "\u0649": ("\u0649", "\ufbe8", "\ufbe9", "\ufef0"),
    # ARABIC LETTER YEH
    "\u064a": ("\u064a", "\ufef3", "\ufef4", "\ufef2"),
    # ARABIC LETTER ALEF WASLA
    "\u0671": ("\u0671", "", "", "\ufb51"),
    # ARABIC LETTER U WITH HAMZA ABOVE
    "\u0677": ("\u0677", "", "", ""),
    # ARABIC LETTER TTEH
    "\u0679": ("\u0679", "\ufb68", "\ufb69", "\ufb67"),
    # ARABIC LETTER TTEHEH
    "\u067a": ("\u067a", "\ufb60", "\ufb61", "\ufb5f"),
    # ARABIC LETTER BEEH
    "\u067b": ("\u067b", "\ufb54", "\ufb55", "\ufb53"),
    # ARABIC LETTER PEH
    "\u067e": ("\u067e", "\ufb58", "\ufb59", "\ufb57"),
    # ARABIC LETTER TEHEH
    "\u067f": ("\u067f", "\ufb64", "\ufb65", "\ufb63"),
    # ARABIC LETTER BEHEH
    "\u0680": ("\u0680", "\ufb5c", "\ufb5d", "\ufb5b"),
    # ARABIC LETTER NYEH
    "\u0683": ("\u0683", "\ufb78", "\ufb79", "\ufb77"),
    # ARABIC LETTER DYEH
    "\u0684": ("\u0684", "\ufb74", "\ufb75", "\ufb73"),
    # ARABIC LETTER TCHEH
    "\u0686": ("\u0686", "\ufb7c", "\ufb7d", "\ufb7b"),
    # ARABIC LETTER TCHEHEH
    "\u0687": ("\u0687", "\ufb80", "\ufb81", "\ufb7f"),
    # ARABIC LETTER DDAL
    "\u0688": ("\u0688", "", "", "\ufb89"),
    # ARABIC LETTER DAHAL
    "\u068c": ("\u068c", "", "", "\ufb85"),
    # ARABIC LETTER DDAHAL
    "\u068d": ("\u068d", "", "", "\ufb83"),
    # ARABIC LETTER DUL
    "\u068e": ("\u068e", "", "", "\ufb87"),
    # ARABIC LETTER RREH
    "\u0691": ("\u0691", "", "", "\ufb8d"),
    # ARABIC LETTER JEH
    "\u0698": ("\u0698", "", "", "\ufb8b"),
    # ARABIC LETTER VEH
    "\u06a4": ("\u06a4", "\ufb6c", "\ufb6d", "\ufb6b"),
    # ARABIC LETTER PEHEH
    "\u06a6": ("\u06a6", "\ufb70", "\ufb71", "\ufb6f"),
    # ARABIC LETTER KEHEH
    "\u06a9": ("\u06a9", "\ufb90", "\ufb91", "\ufb8f"),
    # ARABIC LETTER NG
    "\u06ad": ("\u06ad", "\ufbd5", "\ufbd6", "\ufbd4"),
    # ARABIC LETTER GAF
    "\u06af": ("\u06af", "\ufb94", "\ufb95", "\ufb93"),
    # ARABIC LETTER NGOEH
    "\u06b1": ("\u06b1", "\ufb9c", "\ufb9d", "\ufb9b"),
    # ARABIC LETTER GUEH
    "\u06b3": ("\u06b3", "\ufb98", "\ufb99", "\ufb97"),
    # ARABIC LETTER NOON GHUNNA
    "\u06ba": ("\u06ba", "", "", "\ufb9f"),
    # ARABIC LETTER RNOON
    "\u06bb": ("\u06bb", "\ufba2", "\ufba3", "\ufba1"),
    # ARABIC LETTER HEH DOACHASHMEE
    "\u06be": ("\u06be", "\ufbac", "\ufbad", "\ufbab"),
    # ARABIC LETTER HEH WITH YEH ABOVE
    "\u06c0": ("\u06c0", "", "", "\ufba5"),
    # ARABIC LETTER HEH GOAL
    "\u06c1": ("\u06c1", "\ufba8", "\ufba9", "\ufba7"),
    # ARABIC LETTER KIRGHIZ OE
    "\u06c5": ("\u06c5", "", "", "\ufbe1"),
    # ARABIC LETTER OE
    "\u06c6": ("\u06c6", "", "", "\ufbda"),
    # ARABIC LETTER U
    "\u06c7": ("\u06c7", "", "", "\ufbd8"),
    # ARABIC LETTER YU
    "\u06c8": ("\u06c8", "", "", "\ufbdc"),
    # ARABIC LETTER KIRGHIZ YU
    "\u06c9": ("\u06c9", "", "", "\ufbe3"),
    # ARABIC LETTER VE
    "\u06cb": ("\u06cb", "", "", "\ufbdf"),
    # ARABIC LETTER FARSI YEH
    "\u06cc": ("\u06cc", "\ufbfe", "\ufbff", "\ufbfd"),
    # ARABIC LETTER E
    "\u06d0": ("\u06d0", "\ufbe6", "\ufbe7", "\ufbe5"),
    # ARABIC LETTER YEH BARREE
    "\u06d2": ("\u06d2", "", "", "\ufbaf"),
    # ARABIC LETTER YEH BARREE WITH HAMZA ABOVE
    "\u06d3": ("\u06d3", "", "", "\ufbb1"),
    # Kurdish letter YEAH
    "\u06ce": ("\ue004", "\ue005", "\ue006", "\ue004"),
    # Kurdish letter Hamza same as arabic Teh without the point
    "\u06d5": ("\u06d5", "", "", "\ue000"),
    # ZWJ
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}
LETTERS_KURDISH = {
    # ARABIC LETTER HAMZA
    "\u0621": ("\ufe80", "", "", ""),
    # ARABIC LETTER ALEF WITH MADDA ABOVE
    "\u0622": ("\u0622", "", "", "\ufe82"),
    # ARABIC LETTER ALEF WITH HAMZA ABOVE
    "\u0623": ("\u0623", "", "", "\ufe84"),
    # ARABIC LETTER WAW WITH HAMZA ABOVE
    "\u0624": ("\u0624", "", "", "\ufe86"),
    # ARABIC LETTER ALEF WITH HAMZA BELOW
    "\u0625": ("\u0625", "", "", "\ufe88"),
    # ARABIC LETTER YEH WITH HAMZA ABOVE
    "\u0626": ("\u0626", "\ufe8b", "\ufe8c", "\ufe8a"),
    # ARABIC LETTER ALEF
    "\u0627": ("\u0627", "", "", "\ufe8e"),
    # ARABIC LETTER BEH
    "\u0628": ("\u0628", "\ufe91", "\ufe92", "\ufe90"),
    # ARABIC LETTER TEH MARBUTA
    "\u0629": ("\u0629", "", "", "\ufe94"),
    # ARABIC LETTER TEH
    "\u062a": ("\u062a", "\ufe97", "\ufe98", "\ufe96"),
    # ARABIC LETTER THEH
    "\u062b": ("\u062b", "\ufe9b", "\ufe9c", "\ufe9a"),
    # ARABIC LETTER JEEM
    "\u062c": ("\u062c", "\ufe9f", "\ufea0", "\ufe9e"),
    # ARABIC LETTER HAH
    "\u062d": ("\ufea1", "\ufea3", "\ufea4", "\ufea2"),
    # ARABIC LETTER KHAH
    "\u062e": ("\u062e", "\ufea7", "\ufea8", "\ufea6"),
    # ARABIC LETTER DAL
    "\u062f": ("\u062f", "", "", "\ufeaa"),
    # ARABIC LETTER THAL
    "\u0630": ("\u0630", "", "", "\ufeac"),
    # ARABIC LETTER REH
    "\u0631": ("\u0631", "", "", "\ufeae"),
    # ARABIC LETTER ZAIN
    "\u0632": ("\u0632", "", "", "\ufeb0"),
    # ARABIC LETTER SEEN
    "\u0633": ("\u0633", "\ufeb3", "\ufeb4", "\ufeb2"),
    # ARABIC LETTER SHEEN
    "\u0634": ("\u0634", "\ufeb7", "\ufeb8", "\ufeb6"),
    # ARABIC LETTER SAD
    "\u0635": ("\u0635", "\ufebb", "\ufebc", "\ufeba"),
    # ARABIC LETTER DAD
    "\u0636": ("\u0636", "\ufebf", "\ufec0", "\ufebe"),
    # ARABIC LETTER TAH
    "\u0637": ("\u0637", "\ufec3", "\ufec4", "\ufec2"),
    # ARABIC LETTER ZAH
    "\u0638": ("\u0638", "\ufec7", "\ufec8", "\ufec6"),
    # ARABIC LETTER AIN
    "\u0639": ("\u0639", "\ufecb", "\ufecc", "\ufeca"),
    # ARABIC LETTER GHAIN
    "\u063a": ("\u063a", "\ufecf", "\ufed0", "\ufece"),
    # ARABIC TATWEEL
    TATWEEL: (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    # ARABIC LETTER FEH
    "\u0641": ("\u0641", "\ufed3", "\ufed4", "\ufed2"),
    # ARABIC LETTER QAF
    "\u0642": ("\u0642", "\ufed7", "\ufed8", "\ufed6"),
    # ARABIC LETTER KAF
    "\u0643": ("\u0643", "\ufedb", "\ufedc", "\ufeda"),
    # ARABIC LETTER LAM
    "\u0644": ("\u0644", "\ufedf", "\ufee0", "\ufede"),
    # ARABIC LETTER MEEM
    "\u0645": ("\u0645", "\ufee3", "\ufee4", "\ufee2"),
    # ARABIC LETTER NOON
    "\u0646": ("\u0646", "\ufee7", "\ufee8", "\ufee6"),
    # ARABIC LETTER HEH
    "\u0647": ("\ufbab", "\ufbab", "\ufbab", "\ufbab"),
    # ARABIC LETTER WAW
    "\u0648": ("\u0648", "", "", "\ufeee"),
    # ARABIC LETTER (UIGHUR KAZAKH KIRGHIZ)? ALEF MAKSURA
    "\u0649": ("\u0649", "\ufbe8", "\ufbe9", "\ufef0"),
    # ARABIC LETTER YEH
    "\u064a": ("\u064a", "\ufef3", "\ufef4", "\ufef2"),
    # ARABIC LETTER ALEF WASLA
    "\u0671": ("\u0671", "", "", "\ufb51"),
    # ARABIC LETTER U WITH HAMZA ABOVE
    "\u0677": ("\u0677", "", "", ""),
    # ARABIC LETTER TTEH
    "\u0679": ("\u0679", "\ufb68", "\ufb69", "\ufb67"),
    # ARABIC LETTER TTEHEH
    "\u067a": ("\u067a", "\ufb60", "\ufb61", "\ufb5f"),
    # ARABIC LETTER BEEH
    "\u067b": ("\u067b", "\ufb54", "\ufb55", "\ufb53"),
    # ARABIC LETTER PEH
    "\u067e": ("\u067e", "\ufb58", "\ufb59", "\ufb57"),
    # ARABIC LETTER TEHEH
    "\u067f": ("\u067f", "\ufb64", "\ufb65", "\ufb63"),
    # ARABIC LETTER BEHEH
    "\u0680": ("\u0680", "\ufb5c", "\ufb5d", "\ufb5b"),
    # ARABIC LETTER NYEH
    "\u0683": ("\u0683", "\ufb78", "\ufb79", "\ufb77"),
    # ARABIC LETTER DYEH
    "\u0684": ("\u0684", "\ufb74", "\ufb75", "\ufb73"),
    # ARABIC LETTER TCHEH
    "\u0686": ("\u0686", "\ufb7c", "\ufb7d", "\ufb7b"),
    # ARABIC LETTER TCHEHEH
    "\u0687": ("\u0687", "\ufb80", "\ufb81", "\ufb7f"),
    # ARABIC LETTER DDAL
    "\u0688": ("\u0688", "", "", "\ufb89"),
    # ARABIC LETTER DAHAL
    "\u068c": ("\u068c", "", "", "\ufb85"),
    # ARABIC LETTER DDAHAL
    "\u068d": ("\u068d", "", "", "\ufb83"),
    # ARABIC LETTER DUL
    "\u068e": ("\u068e", "", "", "\ufb87"),
    # ARABIC LETTER RREH
    "\u0691": ("\u0691", "", "", "\ufb8d"),
    # ARABIC LETTER JEH
    "\u0698": ("\u0698", "", "", "\ufb8b"),
    # ARABIC LETTER VEH
    "\u06a4": ("\u06a4", "\ufb6c", "\ufb6d", "\ufb6b"),
    # ARABIC LETTER PEHEH
    "\u06a6": ("\u06a6", "\ufb70", "\ufb71", "\ufb6f"),
    # ARABIC LETTER KEHEH
    "\u06a9": ("\u06a9", "\ufb90", "\ufb91", "\ufb8f"),
    # ARABIC LETTER NG
    "\u06ad": ("\u06ad", "\ufbd5", "\ufbd6", "\ufbd4"),
    # ARABIC LETTER GAF
    "\u06af": ("\u06af", "\ufb94", "\ufb95", "\ufb93"),
    # ARABIC LETTER NGOEH
    "\u06b1": ("\u06b1", "\ufb9c", "\ufb9d", "\ufb9b"),
    # ARABIC LETTER GUEH
    "\u06b3": ("\u06b3", "\ufb98", "\ufb99", "\ufb97"),
    # ARABIC LETTER NOON GHUNNA
    "\u06ba": ("\u06ba", "", "", "\ufb9f"),
    # ARABIC LETTER RNOON
    "\u06bb": ("\u06bb", "\ufba2", "\ufba3", "\ufba1"),
    # ARABIC LETTER HEH DOACHASHMEE
    "\u06be": ("\u06be", "\ufbac", "\ufbad", "\ufbab"),
    # ARABIC LETTER HEH WITH YEH ABOVE
    "\u06c0": ("\u06c0", "", "", "\ufba5"),
    # ARABIC LETTER HEH GOAL
    "\u06c1": ("\u06c1", "\ufba8", "\ufba9", "\ufba7"),
    # ARABIC LETTER KIRGHIZ OE
    "\u06c5": ("\u06c5", "", "", "\ufbe1"),
    # ARABIC LETTER OE
    "\u06c6": ("\u06c6", "", "", "\ufbda"),
    # ARABIC LETTER U
    "\u06c7": ("\u06c7", "", "", "\ufbd8"),
    # ARABIC LETTER YU
    "\u06c8": ("\u06c8", "", "", "\ufbdc"),
    # ARABIC LETTER KIRGHIZ YU
    "\u06c9": ("\u06c9", "", "", "\ufbe3"),
    # ARABIC LETTER VE
    "\u06cb": ("\u06cb", "", "", "\ufbdf"),
    # ARABIC LETTER FARSI YEH
    "\u06cc": ("\u06cc", "\ufbfe", "\ufbff", "\ufbfd"),
    # ARABIC LETTER E
    "\u06d0": ("\u06d0", "\ufbe6", "\ufbe7", "\ufbe5"),
    # ARABIC LETTER YEH BARREE
    "\u06d2": ("\u06d2", "", "", "\ufbaf"),
    # ARABIC LETTER YEH BARREE WITH HAMZA ABOVE
    "\u06d3": ("\u06d3", "", "", "\ufbb1"),
    # Kurdish letter YEAH
    "\u06ce": ("\ue004", "\ue005", "\ue006", "\ue004"),
    # Kurdish letter Hamza same as arabic Teh without the point
    "\u06d5": ("\u06d5", "", "", "\ue000"),
    # ZWJ
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}


def connects_with_letter_before(letter, LETTERS):
    if letter not in LETTERS:
        return False
    forms = LETTERS[letter]
    return forms[FINAL] or forms[MEDIAL]


def connects_with_letter_after(letter, LETTERS):
    if letter not in LETTERS:
        return False
    forms = LETTERS[letter]
    return forms[INITIAL] or forms[MEDIAL]


def connects_with_letters_before_and_after(letter, LETTERS):
    if letter not in LETTERS:
        return False
    forms = LETTERS[letter]
    return forms[MEDIAL]
