# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from .lang_EU import Num2Word_EU


class Num2Word_TE(Num2Word_EU):
    def set_high_numwords(self, high):
        for n, word in self.high_numwords:
            self.cards[10**n] = word

    def setup(self):
        self.low_numwords = [
            "తొంభై తొమ్మిది",
            "తొంభై ఎనిమిది",
            "తొంభై ఏడు",
            "తొంభై ఆరు",
            "తొంభై అయిదు",
            "తొంభై నాలుగు",
            "తొంభై మూడు",
            "తొంభై రెండు",
            "తొంభై ఒకటి",
            "తొంభై",
            "ఎనభై తొమ్మిది",
            "ఎనభై ఎనిమిది",
            "ఎనభై ఏడు",
            "ఎనభై ఆరు",
            "ఎనభై అయిదు",
            "ఎనభై నాలుగు",
            "ఎనభై మూడు",
            "ఎనభై రెండు",
            "ఎనభై ఒకటి",
            "ఎనభై",
            "డెబ్బై తొమ్మిది",
            "డెబ్బై ఎనిమిది",
            "డెబ్బై ఏడు",
            "డెబ్బై ఆరు",
            "డెబ్బై అయిదు",
            "డెబ్బై నాలుగు",
            "డెబ్బై మూడు",
            "డెబ్బై రెండు",
            "డెబ్బై ఒకటి",
            "డెబ్బై",
            "అరవై తొమ్మిది",
            "అరవై ఎనిమిది",
            "అరవై ఏడు",
            "అరవై ఆరు",
            "అరవై అయిదు",
            "అరవై నాలుగు",
            "అరవై మూడు",
            "అరవై రెండు",
            "అరవై ఒకటి",
            "అరవై",
            "యాభై తొమ్మిది",
            "యాభై ఎనిమిది",
            "యాభై ఏడు",
            "యాభై ఆరు",
            "యాభై అయిదు",
            "యాభై నాలుగు",
            "యాభై మూడు",
            "యాభై రెండు",
            "యాభై ఒకటి",
            "యాభై ",
            "నలభై తొమ్మిది",
            "నలభై ఎనిమిది",
            "నలభై ఏడు",
            "నలభై ఆరు",
            "నలభై అయిదు",
            "నలభై నాలుగు",
            "నలభై మూడు",
            "నలభై రెండు",
            "నలభై ఒకటి",
            "నలభై",
            "ముప్పై తొమ్మిది",
            "ముప్పై ఎనిమిది",
            "ముప్పై ఏడు",
            "ముప్పై ఆరు",
            "ముప్పై ఐదు",
            "ముప్పై నాలుగు",
            "ముప్పై మూడు",
            "ముప్పై రెండు",
            "ముప్పై ఒకటి",
            "ముప్పై",
            "ఇరవై తొమ్మిది",
            "ఇరవై ఎనిమిది",
            "ఇరవై ఏడు",
            "ఇరవై ఆరు",
            "ఇరవై అయిదు",
            "ఇరవై నాలుగు",
            "ఇరవై మూడు",
            "ఇరవై రెండు",
            "ఇరవై ఒకటి",
            "ఇరవై",
            "పందొమ్మిది",
            "పధ్ధెనిమిది",
            "పదిహేడు",
            "పదహారు",
            "పదునయిదు",
            "పధ్నాలుగు",
            "పదమూడు",
            "పన్నెండు",
            "పదకొండు",
            "పది",
            "తొమ్మిది",
            "ఎనిమిది",
            "ఏడు",
            "ఆరు",
            "అయిదు",
            "నాలుగు",
            "మూడు",
            "రెండు",
            "ఒకటి",
            "సున్న",
        ]

        self.mid_numwords = [(100, "వంద")]

        self.high_numwords = [(7, "కోట్ల"), (5, "లక్ష"), (3, "వేయి")]

        self.pointword = "బిందువు "

        self.modifiers = [
            " ్  ",
            "ా ",
            " ి ",
            " ీ ",
            " ు ",
            " ూ ",
            " ృ ",
            " ౄ  ",
            " ె ",
            " ే ",
            " ై ",
            " ొ",
            " ో ",
            " ౌ ",
            " ఁ ",
            " ం ",
            " ః ",
        ]

    def merge(self, lpair, rpair):
        ltext, lnum = lpair
        rtext, rnum = rpair
        if lnum == 1 and rnum < 100:
            return (rtext, rnum)
        elif 100 > lnum > rnum:
            return ("%s-%s" % (ltext, rtext), lnum + rnum)
        elif lnum >= 100 > rnum:
            if ltext[-1] in self.modifiers:
                return ("%s %s" % (ltext[:-1], rtext), lnum + rnum)
            else:
                return ("%s %s" % (ltext+"ల", rtext), lnum + rnum)
        elif rnum > lnum:
            return ("%s %s" % (ltext, rtext), lnum * rnum)
        return ("%s %s" % (ltext, rtext), lnum + rnum)

    def to_ordinal_num(self, value):
        self.verify_ordinal(value)
        return "%s%s" % (value, self.to_ordinal(value)[-1:])

    def to_ordinal(self, value):
        self.verify_ordinal(value)
        outwords = self.to_cardinal(value)
        if outwords[-1] in self.modifiers:
            outwords = outwords[:-1]
        ordinal_num = outwords + "వ"
        return ordinal_num
