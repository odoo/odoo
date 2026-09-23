ISOLATED: int = 0
INITIAL: int = 1
MEDIAL: int = 2
FINAL: int = 3

TATWEEL = "\u0640"
ZWJ = "\u200d"
LETTERS_ARABIC = {
    "\u0621": ("\ufe80", "", "", ""),
    "\u0622": ("\ufe81", "", "", "\ufe82"),
    "\u0623": ("\ufe83", "", "", "\ufe84"),
    "\u0624": ("\ufe85", "", "", "\ufe86"),
    "\u0625": ("\ufe87", "", "", "\ufe88"),
    "\u0626": ("\ufe89", "\ufe8b", "\ufe8c", "\ufe8a"),
    "\u0627": ("\ufe8d", "", "", "\ufe8e"),
    "\u0628": ("\ufe8f", "\ufe91", "\ufe92", "\ufe90"),
    "\u0629": ("\ufe93", "", "", "\ufe94"),
    "\u062a": ("\ufe95", "\ufe97", "\ufe98", "\ufe96"),
    "\u062b": ("\ufe99", "\ufe9b", "\ufe9c", "\ufe9a"),
    "\u062c": ("\ufe9d", "\ufe9f", "\ufea0", "\ufe9e"),
    "\u062d": ("\ufea1", "\ufea3", "\ufea4", "\ufea2"),
    "\u062e": ("\ufea5", "\ufea7", "\ufea8", "\ufea6"),
    "\u062f": ("\ufea9", "", "", "\ufeaa"),
    "\u0630": ("\ufeab", "", "", "\ufeac"),
    "\u0631": ("\ufead", "", "", "\ufeae"),
    "\u0632": ("\ufeaf", "", "", "\ufeb0"),
    "\u0633": ("\ufeb1", "\ufeb3", "\ufeb4", "\ufeb2"),
    "\u0634": ("\ufeb5", "\ufeb7", "\ufeb8", "\ufeb6"),
    "\u0635": ("\ufeb9", "\ufebb", "\ufebc", "\ufeba"),
    "\u0636": ("\ufebd", "\ufebf", "\ufec0", "\ufebe"),
    "\u0637": ("\ufec1", "\ufec3", "\ufec4", "\ufec2"),
    "\u0638": ("\ufec5", "\ufec7", "\ufec8", "\ufec6"),
    "\u0639": ("\ufec9", "\ufecb", "\ufecc", "\ufeca"),
    "\u063a": ("\ufecd", "\ufecf", "\ufed0", "\ufece"),
    TATWEEL: (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    "\u0641": ("\ufed1", "\ufed3", "\ufed4", "\ufed2"),
    "\u0642": ("\ufed5", "\ufed7", "\ufed8", "\ufed6"),
    "\u0643": ("\ufed9", "\ufedb", "\ufedc", "\ufeda"),
    "\u0644": ("\ufedd", "\ufedf", "\ufee0", "\ufede"),
    "\u0645": ("\ufee1", "\ufee3", "\ufee4", "\ufee2"),
    "\u0646": ("\ufee5", "\ufee7", "\ufee8", "\ufee6"),
    "\u0647": ("\ufee9", "\ufeeb", "\ufeec", "\ufeea"),
    "\u0648": ("\ufeed", "", "", "\ufeee"),
    "\u0649": ("\ufeef", "\ufbe8", "\ufbe9", "\ufef0"),
    "\u064a": ("\ufef1", "\ufef3", "\ufef4", "\ufef2"),
    "\u0671": ("\ufb50", "", "", "\ufb51"),
    "\u0677": ("\ufbdd", "", "", ""),
    "\u0679": ("\ufb66", "\ufb68", "\ufb69", "\ufb67"),
    "\u067a": ("\ufb5e", "\ufb60", "\ufb61", "\ufb5f"),
    "\u067b": ("\ufb52", "\ufb54", "\ufb55", "\ufb53"),
    "\u067e": ("\ufb56", "\ufb58", "\ufb59", "\ufb57"),
    "\u067f": ("\ufb62", "\ufb64", "\ufb65", "\ufb63"),
    "\u0680": ("\ufb5a", "\ufb5c", "\ufb5d", "\ufb5b"),
    "\u0683": ("\ufb76", "\ufb78", "\ufb79", "\ufb77"),
    "\u0684": ("\ufb72", "\ufb74", "\ufb75", "\ufb73"),
    "\u0686": ("\ufb7a", "\ufb7c", "\ufb7d", "\ufb7b"),
    "\u0687": ("\ufb7e", "\ufb80", "\ufb81", "\ufb7f"),
    "\u0688": ("\ufb88", "", "", "\ufb89"),
    "\u068c": ("\ufb84", "", "", "\ufb85"),
    "\u068d": ("\ufb82", "", "", "\ufb83"),
    "\u068e": ("\ufb86", "", "", "\ufb87"),
    "\u0691": ("\ufb8c", "", "", "\ufb8d"),
    "\u0698": ("\ufb8a", "", "", "\ufb8b"),
    "\u06a4": ("\ufb6a", "\ufb6c", "\ufb6d", "\ufb6b"),
    "\u06a6": ("\ufb6e", "\ufb70", "\ufb71", "\ufb6f"),
    "\u06a9": ("\ufb8e", "\ufb90", "\ufb91", "\ufb8f"),
    "\u06ad": ("\ufbd3", "\ufbd5", "\ufbd6", "\ufbd4"),
    "\u06af": ("\ufb92", "\ufb94", "\ufb95", "\ufb93"),
    "\u06b1": ("\ufb9a", "\ufb9c", "\ufb9d", "\ufb9b"),
    "\u06b3": ("\ufb96", "\ufb98", "\ufb99", "\ufb97"),
    "\u06ba": ("\ufb9e", "", "", "\ufb9f"),
    "\u06bb": ("\ufba0", "\ufba2", "\ufba3", "\ufba1"),
    "\u06be": ("\ufbaa", "\ufbac", "\ufbad", "\ufbab"),
    "\u06c0": ("\ufba4", "", "", "\ufba5"),
    "\u06c1": ("\ufba6", "\ufba8", "\ufba9", "\ufba7"),
    "\u06c5": ("\ufbe0", "", "", "\ufbe1"),
    "\u06c6": ("\ufbd9", "", "", "\ufbda"),
    "\u06c7": ("\ufbd7", "", "", "\ufbd8"),
    "\u06c8": ("\ufbdb", "", "", "\ufbdc"),
    "\u06c9": ("\ufbe2", "", "", "\ufbe3"),
    "\u06cb": ("\ufbde", "", "", "\ufbdf"),
    "\u06cc": ("\ufbfc", "\ufbfe", "\ufbff", "\ufbfd"),
    "\u06d0": ("\ufbe4", "\ufbe6", "\ufbe7", "\ufbe5"),
    "\u06d2": ("\ufbae", "", "", "\ufbaf"),
    "\u06d3": ("\ufbb0", "", "", "\ufbb1"),
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}


def connects_with_letter_before(
    letter: str, LETTERS: dict[str, tuple[str, str, str, str]]
) -> str:
    if letter not in LETTERS:
        return ""
    forms = LETTERS[letter]
    return forms[FINAL] or forms[MEDIAL]


def connects_with_letter_after(
    letter: str, LETTERS: dict[str, tuple[str, str, str, str]]
) -> str:
    if letter not in LETTERS:
        return ""
    forms = LETTERS[letter]
    return forms[INITIAL] or forms[MEDIAL]


def connects_with_letters_before_and_after(
    letter: str, LETTERS: dict[str, tuple[str, str, str, str]]
) -> str:
    if letter not in LETTERS:
        return ""
    forms = LETTERS[letter]
    return forms[MEDIAL]
