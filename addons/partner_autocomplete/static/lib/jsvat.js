/*==================================================================

Application:   Utility Function
Author:        John Gardner
Website:       http://www.braemoor.co.uk/software/vat.shtml

Version:       V1.0
Date:          30th July 2005
Description:   Used to check the validity of an EU country VAT number

Version:       V1.1
Date:          3rd August 2005
Description:   Lithuanian legal entities & Maltese check digit checks added.

Version:       V1.2
Date:          20th October 2005
Description:   Italian checks refined (thanks Matteo Mike Peluso).

Version:       V1.3
Date:          16th November 2005
Description:   Error in GB numbers ending in 00 fixed (thanks Guy Dawson).

Version:       V1.4
Date:          28th September 2006
Description:   EU-type numbers added.

Version:       V1.5
Date:          1st January 2007
Description:   Romanian and Bulgarian numbers added.

Version:       V1.6
Date:          7th January 2007
Description:   Error with Slovenian numbers (thanks to Ales Hotko).

Version:       V1.7
Date:          10th February 2007
Description:   Romanian check digits added.
               Thanks to Dragu Costel for the test suite.

Version:       V1.8
Date:          3rd August 2007
Description:   IE code modified to allow + and * in old format numbers.
               Thanks to Antonin Moy of Sphere Solutions for pointing out the error.

Version:       V1.9
Date:          6th August 2007
Description:   BE code modified to make a specific check that the leading character of 10 digit
               numbers is 0 (belts and braces).

Version:       V1.10
Date:          10th August 2007
Description:   Cypriot check digit support added.
               Check digit validation support for non-standard UK numbers

Version:       V1.11
Date:          25th September 2007
Description:   Spain check digit support for personal numbers.
               Author: David Perez Carmona

Version:       V1.12
Date:          23rd November 2009
Description:   GB code modified to take into account new style check digits.
               Thanks to Guy Dawson of Crossflight Ltd for pointing out the necessity.

Version:       V1.13
Date:          7th July 2012
Description:   EL, GB, SE and BE formats updated - thanks to Joost Van Biervliet of VAT Applications

Version:       V.14
Date:          8th April 2013
Description:   BE Pattern match refined
               BG Add check digit checks for all four types of VAT number
               CY Pattern match improved
               CZ Personal pattern match checking improved
               CZ Personal check digits incorporated
               EE improved pattern match
               ES Physical person number checking refined
               GB Check digit support provided for 12 digit VAT codes and range checks included
               IT Bug removed to allow 999 and 888 issuing office codes
               LT temporarily registered taxpayers check digit support added
               LV Natural persons checks added
               RO improved pattern match
               SK improved pattern match and added check digit support

               Thanks to Theo Vroom for his help in this latest release.

Version:      V1.15
Date:         15th April 2013
              Swedish algorithm re-implemented.

Version:      V1.16
Date:         25th July 2013
              Support for Croatian numbers added

Version       V1.17
              10th September 2013
              Support for Norwegian MVA numbers added (yes, I know that Norway is not in the EU!)

Version       V1.18
              29th October 2013
              Partial support for new style Irish numbers.
              See http://www.revenue.ie/en/practitioner/ebrief/2013/no-032013.html
              Thanks to Simon Leigh for drawing the author's attention to this.

Version       V1.19
              31st October 2013
              Support for Serbian PBI numbers added (yes, I know that Serbia is not in the EU!)

Version       V1.20
              1st November 2013
              Support for Swiss MWST numbers added (yes, I know that Switzerland is not in the EU!)

Version       V1.21
              16th December 2014
              Non-critical code tidies to French and Danish regular expressions.
              Thanks to Bill Seddon of Lyquidity Solutions

Version       V1.22
              14th January 2014
              Non-critical code tidy to regular expression for new format Irish numbers.
              Thanks to Olivier Reubens of UNIT4 C-Logic N.V.

Version       V1.23
              10th April 2014
              Support for Russian INN numbers added (yes, I know that Russia is not in the EU!).
              Thanks to Marco Cesaratto of Arki Tech, Italy

Version       V1.24
              4th June 2014
              Check digit validation supported for Irish Type 3 numbers
              Thanks to Olivier Reubens of UNIT4 C-Logic N.V.

Version       V1.25
              29th July 2014
              Code improvements
              Thanks to Sébastien Boelpaep and Nate Kerkhofs

Version       V1.26
              4th May 2015
              Code improvements to regular expressions
              Thanks to Robert Gust-Bardon of webcraft.ch

Version       V1.27
              3rd December 2015
              Extend Swiss optional suffix to allow TVA and ITA
              Thanks to Oskars Petermanis

Version       V1.28
              30th August 2016
              Correct Swiss optional suffix to allow TVA and IVA
              Thanks to Jan Verhaegen

Version       V1.29
              29th July 2017
              Correct Czeck Republic checking of Individual type 2 - Special Cases
              Thanks to Andreas Wuermser of Auer Packaging UK

Parameters:    toCheck - VAT number be checked.

This function checks the value of the parameter for a valid European VAT number.

If the number is found to be invalid format, the function returns a value of false. Otherwise it
returns the VAT number re-formatted.

Example call:

  if (checkVATNumber (myVATNumber))
      alert ("VAT number has a valid format")
  else
      alert ("VAT number has invalid format");

---------------------------------------------------------------------------------------------------*/

var checkVATNumber = (function (){
    // Array holds the regular expressions for the valid VAT number
    var vatexp = new Array();

    // To change the default country (e.g. from the UK to Germany - DE):
    //    1.  Change the country code in the defCCode variable below to "DE".
    //    2.  Remove the question mark from the regular expressions associated with the UK VAT number:
    //        i.e. "(GB)?" -> "(GB)"
    //    3.  Add a question mark into the regular expression associated with Germany's number
    //        following the country code: i.e. "(DE)" -> "(DE)?"

    var defCCode = "GB";

    // Note - VAT codes without the "**" in the comment do not have check digit checking.

    vatexp.push(/^(AT)U(\d{8})$/);                           //** Austria
    vatexp.push(/^(BE)(0?\d{9})$/);                          //** Belgium
    vatexp.push(/^(BG)(\d{9,10})$/);                         //** Bulgaria
    vatexp.push(/^(CHE)(\d{9})(MWST|TVA|IVA)?$/);            //** Switzerland
    vatexp.push(/^(CY)([0-59]\d{7}[A-Z])$/);                 //** Cyprus
    vatexp.push(/^(CZ)(\d{8,10})(\d{3})?$/);                 //** Czech Republic
    vatexp.push(/^(DE)([1-9]\d{8})$/);                       //** Germany
    vatexp.push(/^(DK)(\d{8})$/);                            //** Denmark
    vatexp.push(/^(EE)(10\d{7})$/);                          //** Estonia
    vatexp.push(/^(EL)(\d{9})$/);                            //** Greece
    vatexp.push(/^(ES)([A-Z]\d{8})$/);                       //** Spain (National juridical entities)
    vatexp.push(/^(ES)([A-HN-SW]\d{7}[A-J])$/);              //** Spain (Other juridical entities)
    vatexp.push(/^(ES)([0-9YZ]\d{7}[A-Z])$/);                //** Spain (Personal entities type 1)
    vatexp.push(/^(ES)([KLMX]\d{7}[A-Z])$/);                 //** Spain (Personal entities type 2)
    vatexp.push(/^(EU)(\d{9})$/);                            //** EU-type
    vatexp.push(/^(FI)(\d{8})$/);                            //** Finland
    vatexp.push(/^(FR)(\d{11})$/);                           //** France (1)
    vatexp.push(/^(FR)([A-HJ-NP-Z]\d{10})$/);                // France (2)
    vatexp.push(/^(FR)(\d[A-HJ-NP-Z]\d{9})$/);               // France (3)
    vatexp.push(/^(FR)([A-HJ-NP-Z]{2}\d{9})$/);              // France (4)
    vatexp.push(/^(GB)?(\d{9})$/);                           //** UK (Standard)
    vatexp.push(/^(GB)?(\d{12})$/);                          //** UK (Branches)
    vatexp.push(/^(GB)?(GD\d{3})$/);                         //** UK (Government)
    vatexp.push(/^(GB)?(HA\d{3})$/);                         //** UK (Health authority)
    vatexp.push(/^(HR)(\d{11})$/);                           //** Croatia
    vatexp.push(/^(HU)(\d{8})$/);                            //** Hungary
    vatexp.push(/^(IE)(\d{7}[A-W])$/);                       //** Ireland (1)
    vatexp.push(/^(IE)([7-9][A-Z\*\+)]\d{5}[A-W])$/);        //** Ireland (2)
    vatexp.push(/^(IE)(\d{7}[A-W][AH])$/);                   //** Ireland (3)
    vatexp.push(/^(IT)(\d{11})$/);                           //** Italy
    vatexp.push(/^(LV)(\d{11})$/);                           //** Latvia
    vatexp.push(/^(LT)(\d{9}|\d{12})$/);                     //** Lithunia
    vatexp.push(/^(LU)(\d{8})$/);                            //** Luxembourg
    vatexp.push(/^(MT)([1-9]\d{7})$/);                       //** Malta
    vatexp.push(/^(NL)(\d{9})B\d{2}$/);                      //** Netherlands
    vatexp.push(/^(NO)(\d{9})$/);                            //** Norway (not EU)
    vatexp.push(/^(PL)(\d{10})$/);                           //** Poland
    vatexp.push(/^(PT)(\d{9})$/);                            //** Portugal
    vatexp.push(/^(RO)([1-9]\d{1,9})$/);                     //** Romania
    vatexp.push(/^(RU)(\d{10}|\d{12})$/);                    //** Russia
    vatexp.push(/^(RS)(\d{9})$/);                            //** Serbia
    vatexp.push(/^(SI)([1-9]\d{7})$/);                       //** Slovenia
    vatexp.push(/^(SK)([1-9]\d[2346-9]\d{7})$/);             //** Slovakia Republic
    vatexp.push(/^(SE)(\d{10}01)$/);                         //** Sweden

    function checkVATNumber(toCheck) {
        // Load up the string to check
        var VATNumber = toCheck.toUpperCase();

        // Remove spaces etc. from the VAT number to help validation
        VATNumber = VATNumber.replace(/(\s|-|\.)+/g, '');

        // Assume we're not going to find a valid VAT number
        var valid = false;

        // Check the string against the regular expressions for all types of VAT numbers
        for (var i = 0; i < vatexp.length; i++) {

            // Have we recognised the VAT number?
            if (vatexp[i].test(VATNumber)) {

                // Yes - we have
                var cCode = RegExp.$1;                             // Isolate country code
                var cNumber = RegExp.$2;                           // Isolate the number
                if (cCode.length == 0) cCode = defCCode;           // Set up default country code

                // Call the appropriate country VAT validation routine depending on the country code
                if (eval(cCode + "VATCheckDigit ('" + cNumber + "')")) valid = VATNumber;

                // Having processed the number, we break from the loop
                break;
            }
        }

        // Return with either an error or the reformatted VAT number
        return valid;
    }

    function ATVATCheckDigit(vatnumber) {

        // Checks the check digits of an Austrian VAT number.

        var total = 0;
        var multipliers = [1, 2, 1, 2, 1, 2, 1];
        var temp = 0;

        // Extract the next digit and multiply by the appropriate multiplier.
        for (var i = 0; i < 7; i++) {
            temp = Number(vatnumber.charAt(i)) * multipliers[i];
            if (temp > 9)
                total += Math.floor(temp / 10) + temp % 10;
            else
                total += temp;
        }

        // Establish check digit.
        total = 10 - (total + 4) % 10;
        if (total == 10) total = 0;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(7, 8))
            return true;
        else
            return false;
    }

    function BEVATCheckDigit(vatnumber) {

        // Checks the check digits of a Belgium VAT number.

        // Nine digit numbers have a 0 inserted at the front.
        if (vatnumber.length == 9) vatnumber = "0" + vatnumber;

        if (vatnumber.slice(1, 2) == 0) return false;

        // Modulus 97 check on last nine digits
        if (97 - vatnumber.slice(0, 8) % 97 == vatnumber.slice(8, 10))
            return true;
        else
            return false;
    }

    function BGVATCheckDigit(vatnumber) {
        var temp, total, multipliers, i;

        // Checks the check digits of a Bulgarian VAT number.

        if (vatnumber.length == 9) {
            // Check the check digit of 9 digit Bulgarian VAT numbers.
            total = 0;

            // First try to calculate the check digit using the first multipliers
            temp = 0;
            for (i = 0; i < 8; i++) temp += Number(vatnumber.charAt(i)) * (i + 1);

            // See if we have a check digit yet
            total = temp % 11;
            if (total != 10) {
                if (total == vatnumber.slice(8))
                    return true;
                else
                    return false;
            }

            // We got a modulus of 10 before so we have to keep going. Calculate the new check digit using
            // the different multipliers
            temp = 0;
            for (i = 0; i < 8; i++) temp += Number(vatnumber.charAt(i)) * (i + 3);

            // See if we have a check digit yet. If we still have a modulus of 10, set it to 0.
            total = temp % 11;
            if (total == 10) total = 0;
            if (total == vatnumber.slice(8))
                return true;
            else
                return false;
        }

        // 10 digit VAT code - see if it relates to a standard physical person
        if ((/^\d\d[0-5]\d[0-3]\d\d{4}$/).test(vatnumber)) {

            // Check month
            var month = Number(vatnumber.slice(2, 4));
            if ((month > 0 && month < 13) || (month > 20 && month < 33) || (month > 40 && month < 53)) {

                // Extract the next digit and multiply by the counter.
                multipliers = [2, 4, 8, 5, 10, 9, 7, 3, 6];
                total = 0;
                for (i = 0; i < 9; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

                // Establish check digit.
                total = total % 11;
                if (total == 10) total = 0;

                // Check to see if the check digit given is correct, If not, try next type of person
                if (total == vatnumber.substr(9, 1)) return true;
            }
        }

        // It doesn't relate to a standard physical person - see if it relates to a foreigner.

        // Extract the next digit and multiply by the counter.
        multipliers = [21, 19, 17, 13, 11, 9, 7, 3, 1];
        total = 0;
        for (i = 0; i < 9; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Check to see if the check digit given is correct, If not, try next type of person
        if (total % 10 == vatnumber.substr(9, 1)) return true;

        // Finally, if not yet identified, see if it conforms to a miscellaneous VAT number

        // Extract the next digit and multiply by the counter.
        multipliers = [4, 3, 2, 7, 6, 5, 4, 3, 2];
        total = 0;
        for (i = 0; i < 9; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = 11 - total % 11;
        if (total == 10) return false;
        if (total == 11) total = 0;

        // Check to see if the check digit given is correct, If not, we have an error with the VAT number
        if (total == vatnumber.substr(9, 1))
            return true;
        else
            return false;
    }

    function CHEVATCheckDigit(vatnumber) {

        // Checks the check digits of a Swiss VAT number.

        // Extract the next digit and multiply by the counter.
        var multipliers = [5, 4, 3, 2, 7, 6, 5, 4];
        var total = 0;
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = 11 - total % 11;
        if (total == 10) return false;
        if (total == 11) total = 0;

        // Check to see if the check digit given is correct, If not, we have an error with the VAT number
        if (total == vatnumber.substr(8, 1))
            return true;
        else
            return false;
    }

    function CYVATCheckDigit(vatnumber) {

        // Checks the check digits of a Cypriot VAT number.

        // Not allowed to start with '12'
        if (Number(vatnumber.slice(0, 2) == 12)) return false;

        // Extract the next digit and multiply by the counter.
        var total = 0;
        for (var i = 0; i < 8; i++) {
            var temp = Number(vatnumber.charAt(i));
            if (i % 2 == 0) {
                switch (temp) {
                    case 0:
                        temp = 1;
                        break;
                    case 1:
                        temp = 0;
                        break;
                    case 2:
                        temp = 5;
                        break;
                    case 3:
                        temp = 7;
                        break;
                    case 4:
                        temp = 9;
                        break;
                    default:
                        temp = temp * 2 + 3;
                }
            }
            total += temp;
        }

        // Establish check digit using modulus 26, and translate to char. equivalent.
        total = total % 26;
        total = String.fromCharCode(total + 65);

        // Check to see if the check digit given is correct
        if (total == vatnumber.substr(8, 1))
            return true;
        else
            return false;
    }

    function CZVATCheckDigit(vatnumber) {

        // Checks the check digits of a Czech Republic VAT number.

        var total = 0;
        var multipliers = [8, 7, 6, 5, 4, 3, 2];

        var czexp = new Array();
        czexp[0] = (/^\d{8}$/);                                       //  8 digit legal entities
        // Note - my specification says that that the following should have a range of 0-3 in the fourth
        // digit, but the valid number CZ395601439 did not confrm, so a range of 0-9 has been allowed.
        czexp[1] = (/^[0-5][0-9][0|1|5|6][0-9][0-3][0-9]\d{3}$/);     //  9 digit individuals
        czexp[2] = (/^6\d{8}$/);                                      //  9 digit individuals (Special cases)
        czexp[3] = (/^\d{2}[0-3|5-8][0-9][0-3][0-9]\d{4}$/);          // 10 digit individuals
        var i = 0;
        var a;

        // Legal entities
        if (czexp[0].test(vatnumber)) {

            // Extract the next digit and multiply by the counter.
            for (i = 0; i < 7; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

            // Establish check digit.
            total = 11 - total % 11;
            if (total == 10) total = 0;
            if (total == 11) total = 1;

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(7, 8))
                return true;
            else
                return false;
        }

        // Individuals type 1 (Standard) - 9 digits without check digit
        else if (czexp[1].test(vatnumber)) {
            if (Number(vatnumber.slice(0, 2)) > 62) return false;
            return true;
        }

        // Individuals type 2 (Special Cases) - 9 digits including check digit
        else if (czexp[2].test(vatnumber)) {

            // Extract the next digit and multiply by the counter.
            for (i = 0; i < 7; i++) total += Number(vatnumber.charAt(i + 1)) * multipliers[i];

            // Establish check digit pointer into lookup table
            if (total % 11 == 0)
                a = total + 11;
            else
                a = Math.ceil(total / 11) * 11;
            var pointer = a - total;

            // Convert calculated check digit according to a lookup table;
            var lookup = [8, 7, 6, 5, 4, 3, 2, 1, 0, 9, 8];
            if (lookup[pointer - 1] == vatnumber.slice(8, 9))
                return true;
            else
                return false;
        }

        // Individuals type 3 - 10 digits
        else if (czexp[3].test(vatnumber)) {
            var temp = Number(vatnumber.slice(0, 2)) + Number(vatnumber.slice(2, 4)) + Number(vatnumber.slice(4, 6)) + Number(vatnumber.slice(6, 8)) + Number(vatnumber.slice(8));
            if (temp % 11 == 0 && Number(vatnumber) % 11 == 0)
                return true;
            else
                return false;
        }

        // else error
        return false;
    }

    function DEVATCheckDigit(vatnumber) {

        // Checks the check digits of a German VAT number.

        var product = 10;
        var sum = 0;
        var checkdigit = 0;
        for (var i = 0; i < 8; i++) {

            // Extract the next digit and implement peculiar algorithm!.
            sum = (Number(vatnumber.charAt(i)) + product) % 10;
            if (sum == 0) {
                sum = 10;
            }
            product = (2 * sum) % 11;
        }

        // Establish check digit.
        if (11 - product == 10) {
            checkdigit = 0;
        } else {
            checkdigit = 11 - product;
        }

        // Compare it with the last two characters of the VAT number. If the same, then it is a valid
        // check digit.
        if (checkdigit == vatnumber.slice(8, 9))
            return true;
        else
            return false;
    }

    function DKVATCheckDigit(vatnumber) {

        // Checks the check digits of a Danish VAT number.

        var total = 0;
        var multipliers = [2, 7, 6, 5, 4, 3, 2, 1];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = total % 11;

        // The remainder should be 0 for it to be valid..
        if (total == 0)
            return true;
        else
            return false;
    }

    function EEVATCheckDigit(vatnumber) {

        // Checks the check digits of an Estonian VAT number.

        var total = 0;
        var multipliers = [3, 7, 1, 3, 7, 1, 3, 7];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits using modulus 10.
        total = 10 - total % 10;
        if (total == 10) total = 0;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(8, 9))
            return true;
        else
            return false;
    }

    function ELVATCheckDigit(vatnumber) {

        // Checks the check digits of a Greek VAT number.

        var total = 0;
        var multipliers = [256, 128, 64, 32, 16, 8, 4, 2];

        //eight character numbers should be prefixed with an 0.
        if (vatnumber.length == 8) {
            vatnumber = "0" + vatnumber;
        }

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = total % 11;
        if (total > 9) {
            total = 0;
        }

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(8, 9))
            return true;
        else
            return false;
    }

    function ESVATCheckDigit(vatnumber) {

        // Checks the check digits of a Spanish VAT number.

        var total = 0;
        var temp = 0;
        var multipliers = [2, 1, 2, 1, 2, 1, 2];
        var esexp = new Array();
        esexp[0] = (/^[A-H|J|U|V]\d{8}$/);
        esexp[1] = (/^[A-H|N-S|W]\d{7}[A-J]$/);
        esexp[2] = (/^[0-9|Y|Z]\d{7}[A-Z]$/);
        esexp[3] = (/^[K|L|M|X]\d{7}[A-Z]$/);
        var i = 0;

        // National juridical entities
        if (esexp[0].test(vatnumber)) {

            // Extract the next digit and multiply by the counter.
            for (i = 0; i < 7; i++) {
                temp = Number(vatnumber.charAt(i + 1)) * multipliers[i];
                if (temp > 9)
                    total += Math.floor(temp / 10) + temp % 10;
                else
                    total += temp;
            }
            // Now calculate the check digit itself.
            total = 10 - total % 10;
            if (total == 10) {
                total = 0;
            }

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(8, 9))
                return true;
            else
                return false;
        }

        // Juridical entities other than national ones
        else if (esexp[1].test(vatnumber)) {

            // Extract the next digit and multiply by the counter.
            for (i = 0; i < 7; i++) {
                temp = Number(vatnumber.charAt(i + 1)) * multipliers[i];
                if (temp > 9)
                    total += Math.floor(temp / 10) + temp % 10;
                else
                    total += temp;
            }

            // Now calculate the check digit itself.
            total = 10 - total % 10;
            total = String.fromCharCode(total + 64);

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(8, 9))
                return true;
            else
                return false;
        }

        // Personal number (NIF) (starting with numeric of Y or Z)
        else if (esexp[2].test(vatnumber)) {
            var tempnumber = vatnumber;
            if (tempnumber.substring(0, 1) == 'Y') tempnumber = tempnumber.replace(/Y/, "1");
            if (tempnumber.substring(0, 1) == 'Z') tempnumber = tempnumber.replace(/Z/, "2");
            return tempnumber.charAt(8) == 'TRWAGMYFPDXBNJZSQVHLCKE'.charAt(Number(tempnumber.substring(0, 8)) % 23);
        }

        // Personal number (NIF) (starting with K, L, M, or X)
        else if (esexp[3].test(vatnumber)) {
            return vatnumber.charAt(8) == 'TRWAGMYFPDXBNJZSQVHLCKE'.charAt(Number(vatnumber.substring(1, 8)) % 23);
        }

        else return false;
    }

    function EUVATCheckDigit(vatnumber) {

        // We know little about EU numbers apart from the fact that the first 3 digits represent the
        // country, and that there are nine digits in total.
        return true;
    }

    function FIVATCheckDigit(vatnumber) {

        // Checks the check digits of a Finnish VAT number.

        var total = 0;
        var multipliers = [7, 9, 10, 5, 8, 4, 2];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = 11 - total % 11;
        if (total > 9) {
            total = 0;
        }

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(7, 8))
            return true;
        else
            return false;
    }

    function FRVATCheckDigit(vatnumber) {

        // Checks the check digits of a French VAT number.

        if (!(/^\d{11}$/).test(vatnumber)) return true;

        // Extract the last nine digits as an integer.
        var total = vatnumber.substring(2);

        // Establish check digit.
        total = (total * 100 + 12) % 97;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(0, 2))
            return true;
        else
            return false;
    }

    function GBVATCheckDigit(vatnumber) {

        // Checks the check digits of a UK VAT number.

        var multipliers = [8, 7, 6, 5, 4, 3, 2];

        // Government departments
        if (vatnumber.substr(0, 2) == 'GD') {
            if (vatnumber.substr(2, 3) < 500)
                return true;
            else
                return false;
        }

        // Health authorities
        if (vatnumber.substr(0, 2) == 'HA') {
            if (vatnumber.substr(2, 3) > 499)
                return true;
            else
                return false;
        }

        // Standard and commercial numbers
        var total = 0;

        // 0 VAT numbers disallowed!
        if (Number(vatnumber.slice(0)) == 0) return false;

        // Check range is OK for modulus 97 calculation
        var no = Number(vatnumber.slice(0, 7));

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Old numbers use a simple 97 modulus, but new numbers use an adaptation of that (less 55). Our
        // VAT number could use either system, so we check it against both.

        // Establish check digits by subtracting 97 from total until negative.
        var cd = total;
        while (cd > 0) {
            cd = cd - 97;
        }

        // Get the absolute value and compare it with the last two characters of the VAT number. If the
        // same, then it is a valid traditional check digit. However, even then the number must fit within
        // certain specified ranges.
        cd = Math.abs(cd);
        if (cd == vatnumber.slice(7, 9) && no < 9990001 && (no < 100000 || no > 999999) && (no < 9490001 || no > 9700000)) return true;

        // Now try the new method by subtracting 55 from the check digit if we can - else add 42
        if (cd >= 55)
            cd = cd - 55;
        else
            cd = cd + 42;
        if (cd == vatnumber.slice(7, 9) && no > 1000000)
            return true;
        else
            return false;
    }

    function HRVATCheckDigit(vatnumber) {

        // Checks the check digits of a Croatian VAT number using ISO 7064, MOD 11-10 for check digit.

        var product = 10;
        var sum = 0;
        var checkdigit = 0;

        for (var i = 0; i < 10; i++) {

            // Extract the next digit and implement the algorithm
            sum = (Number(vatnumber.charAt(i)) + product) % 10;
            if (sum == 0) {
                sum = 10;
            }
            product = (2 * sum) % 11;
        }

        // Now check that we have the right check digit
        if ((product + vatnumber.slice(10, 11) * 1) % 10 == 1)
            return true;
        else
            return false;
    }

    function HUVATCheckDigit(vatnumber) {

        // Checks the check digits of a Hungarian VAT number.

        var total = 0;
        var multipliers = [9, 7, 3, 1, 9, 7, 3];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = 10 - total % 10;
        if (total == 10) total = 0;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(7, 8))
            return true;
        else
            return false;
    }

    function IEVATCheckDigit(vatnumber) {

        // Checks the check digits of an Irish VAT number.

        var total = 0;
        var multipliers = [8, 7, 6, 5, 4, 3, 2];

        // If the code is type 1 format, we need to convert it to the new before performing the validation.
        if (/^\d[A-Z\*\+]/.test(vatnumber)) vatnumber = "0" + vatnumber.substring(2, 7) + vatnumber.substring(0, 1) + vatnumber.substring(7, 8);

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // If the number is type 3 then we need to include the trailing A or H in the calculation
        if (/^\d{7}[A-Z][AH]$/.test(vatnumber)) {

            // Add in a multiplier for the character A (1*9=9) or H (8*9=72)
            if (vatnumber.charAt(8) == 'H')
                total += 72;
            else
                total += 9;
        }

        // Establish check digit using modulus 23, and translate to char. equivalent.
        total = total % 23;
        if (total == 0)
            total = "W";
        else
            total = String.fromCharCode(total + 64);

        // Compare it with the eighth character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(7, 8))
            return true;
        else
            return false;
    }

    function ITVATCheckDigit(vatnumber) {

        // Checks the check digits of an Italian VAT number.

        var total = 0;
        var multipliers = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2];
        var temp;

        // The last three digits are the issuing office, and cannot exceed more 201, unless 999 or 888
        if (Number(vatnumber.slice(0, 7)) == 0) return false;
        temp = Number(vatnumber.slice(7, 10));
        if ((temp < 1) || (temp > 201) && temp != 999 && temp != 888) return false;

        // Extract the next digit and multiply by the appropriate
        for (var i = 0; i < 10; i++) {
            temp = Number(vatnumber.charAt(i)) * multipliers[i];
            if (temp > 9)
                total += Math.floor(temp / 10) + temp % 10;
            else
                total += temp;
        }

        // Establish check digit.
        total = 10 - total % 10;
        if (total > 9) {
            total = 0;
        }

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(10, 11))
            return true;
        else
            return false;
    }

    function LTVATCheckDigit(vatnumber) {

        // Checks the check digits of a Lithuanian VAT number.
        var total, multipliers, i;

        // 9 character VAT numbers are for legal persons
        if (vatnumber.length == 9) {

            // 8th character must be one
            if (!(/^\d{7}1/).test(vatnumber)) return false;

            // Extract the next digit and multiply by the counter+1.
            total = 0;
            for (i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * (i + 1);

            // Can have a double check digit calculation!
            if (total % 11 == 10) {
                multipliers = [3, 4, 5, 6, 7, 8, 9, 1];
                total = 0;
                for (i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];
            }

            // Establish check digit.
            total = total % 11;
            if (total == 10) {
                total = 0;
            }

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(8, 9))
                return true;
            else
                return false;
        }

        // 12 character VAT numbers are for temporarily registered taxpayers
        else {

            // 11th character must be one
            if (!(/^\d{10}1/).test(vatnumber)) return false;

            // Extract the next digit and multiply by the counter+1.
            total = 0;
            multipliers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2];
            for (i = 0; i < 11; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

            // Can have a double check digit calculation!
            if (total % 11 == 10) {
                multipliers = [3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4];
                total = 0;
                for (i = 0; i < 11; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];
            }

            // Establish check digit.
            total = total % 11;
            if (total == 10) {
                total = 0;
            }

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(11, 12))
                return true;
            else
                return false;
        }
    }

    function LUVATCheckDigit(vatnumber) {

        // Checks the check digits of a Luxembourg VAT number.

        if (vatnumber.slice(0, 6) % 89 == vatnumber.slice(6, 8))
            return true;
        else
            return false;
    }

    function LVVATCheckDigit(vatnumber) {

        // Checks the check digits of a Latvian VAT number.

        // Differentiate between legal entities and natural bodies. For the latter we simply check that
        // the first six digits correspond to valid DDMMYY dates.
        if ((/^[0-3]/).test(vatnumber)) {
            if ((/^[0-3][0-9][0-1][0-9]/).test(vatnumber))
                return true;
            else
                return false;
        }

        else {

            var total = 0;
            var multipliers = [9, 1, 4, 8, 3, 10, 2, 5, 7, 6];

            // Extract the next digit and multiply by the counter.
            for (var i = 0; i < 10; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

            // Establish check digits by getting modulus 11.
            if (total % 11 == 4 && vatnumber[0] == 9) total = total - 45;
            if (total % 11 == 4)
                total = 4 - total % 11;
            else if (total % 11 > 4)
                total = 14 - total % 11;
            else if (total % 11 < 4)
                total = 3 - total % 11;

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(10, 11))
                return true;
            else
                return false;
        }
    }

    function MTVATCheckDigit(vatnumber) {

        // Checks the check digits of a Maltese VAT number.

        var total = 0;
        var multipliers = [3, 4, 6, 7, 8, 9];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 6; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits by getting modulus 37.
        total = 37 - total % 37;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(6, 8) * 1)
            return true;
        else
            return false;
    }

    function NLVATCheckDigit(vatnumber) {

        // Checks the check digits of a Dutch VAT number.

        var total = 0;
        var multipliers = [9, 8, 7, 6, 5, 4, 3, 2];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits by getting modulus 11.
        total = total % 11;
        if (total > 9) {
            total = 0;
        }

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(8, 9))
            return true;
        else
            return false;
    }

    function NOVATCheckDigit(vatnumber) {

        // Checks the check digits of a Norwegian VAT number.
        // See http://www.brreg.no/english/coordination/number.html

        var total = 0;
        var multipliers = [3, 2, 7, 6, 5, 4, 3, 2];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits by getting modulus 11. Check digits > 9 are invalid
        total = 11 - total % 11;
        if (total == 11) {
            total = 0;
        }
        if (total < 10) {

            // Compare it with the last character of the VAT number. If it's the same, then it's valid.
            if (total == vatnumber.slice(8, 9))
                return true;
            else
                return false;
        }
    }

    function PLVATCheckDigit(vatnumber) {

        // Checks the check digits of a Polish VAT number.

        var total = 0;
        var multipliers = [6, 5, 7, 2, 3, 4, 5, 6, 7];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 9; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits subtracting modulus 11 from 11.
        total = total % 11;
        if (total > 9) {
            total = 0;
        }

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(9, 10))
            return true;
        else
            return false;
    }

    function PTVATCheckDigit(vatnumber) {

        // Checks the check digits of a Portugese VAT number.

        var total = 0;
        var multipliers = [9, 8, 7, 6, 5, 4, 3, 2];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 8; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits subtracting modulus 11 from 11.
        total = 11 - total % 11;
        if (total > 9) {
            total = 0;
        }

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(8, 9))
            return true;
        else
            return false;
    }

    function ROVATCheckDigit(vatnumber) {

        // Checks the check digits of a Romanian VAT number.

        var multipliers = [7, 5, 3, 2, 1, 7, 5, 3, 2];

        // Extract the next digit and multiply by the counter.
        var VATlen = vatnumber.length;
        multipliers = multipliers.slice(10 - VATlen);
        var total = 0;
        for (var i = 0; i < vatnumber.length - 1; i++) {
            total += Number(vatnumber.charAt(i)) * multipliers[i];
        }

        // Establish check digits by getting modulus 11.
        total = (10 * total) % 11;
        if (total == 10) total = 0;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (total == vatnumber.slice(vatnumber.length - 1, vatnumber.length))
            return true;
        else
            return false;
    }

    function RSVATCheckDigit(vatnumber) {

        // Checks the check digits of a Serbian VAT number using ISO 7064, MOD 11-10 for check digit.

        var product = 10;
        var sum = 0;
        var checkdigit = 0;

        for (var i = 0; i < 8; i++) {

            // Extract the next digit and implement the algorithm
            sum = (Number(vatnumber.charAt(i)) + product) % 10;
            if (sum == 0) {
                sum = 10;
            }
            product = (2 * sum) % 11;
        }

        // Now check that we have the right check digit
        if ((product + vatnumber.slice(8, 9) * 1) % 10 == 1)
            return true;
        else
            return false;
    }

    function RUVATCheckDigit(vatnumber) {

        // Checks the check digits of a Russian INN number
        // See http://russianpartner.biz/test_inn.html for algorithm

        var i;

        // 10 digit INN numbers
        if (vatnumber.length == 10) {
            var total = 0;
            var multipliers = [2, 4, 10, 3, 5, 9, 4, 6, 8, 0];
            for (i = 0; i < 10; i++) {
                total += Number(vatnumber.charAt(i)) * multipliers[i];
            }
            total = total % 11;
            if (total > 9) {
                total = total % 10;
            }

            // Compare it with the last character of the VAT number. If it is the same, then it's valid
            if (total == vatnumber.slice(9, 10))
                return true;
            else
                return false;

            // 12 digit INN numbers
        } else if (vatnumber.length == 12) {
            var total1 = 0;
            var multipliers1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0];
            var total2 = 0;
            var multipliers2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0];

            for (i = 0; i < 11; i++) total1 += Number(vatnumber.charAt(i)) * multipliers1[i];
            total1 = total1 % 11;
            if (total1 > 9) {
                total1 = total1 % 10;
            }

            for (i = 0; i < 11; i++) total2 += Number(vatnumber.charAt(i)) * multipliers2[i];
            total2 = total2 % 11;
            if (total2 > 9) {
                total2 = total2 % 10;
            }

            // Compare the first check with the 11th character and the second check with the 12th and last
            // character of the VAT number. If they're both the same, then it's valid
            if ((total1 == vatnumber.slice(10, 11)) && (total2 == vatnumber.slice(11, 12)))
                return true;
            else
                return false;
        }
    }

    function SEVATCheckDigit(vatnumber) {
        var i;

        // Calculate R where R = R1 + R3 + R5 + R7 + R9, and Ri = INT(Ci/5) + (Ci*2) modulo 10
        var R = 0;
        var digit;
        for (i = 0; i < 9; i = i + 2) {
            digit = Number(vatnumber.charAt(i));
            R += Math.floor(digit / 5) + ((digit * 2) % 10);
        }

        // Calculate S where S = C2 + C4 + C6 + C8
        var S = 0;
        for (i = 1; i < 9; i = i + 2) S += Number(vatnumber.charAt(i));

        // Calculate the Check Digit
        var cd = (10 - (R + S) % 10) % 10;

        // Compare it with the last character of the VAT number. If it's the same, then it's valid.
        if (cd == vatnumber.slice(9, 10))
            return true;
        else
            return false;
    }

    function SIVATCheckDigit(vatnumber) {

        // Checks the check digits of a Slovenian VAT number.

        var total = 0;
        var multipliers = [8, 7, 6, 5, 4, 3, 2];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total += Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits using modulus 11
        total = 11 - total % 11;
        if (total == 10) {
            total = 0;
        }

        // Compare the number with the last character of the VAT number. If it is the
        // same, then it's a valid check digit.
        if (total != 11 && total == vatnumber.slice(7, 8))
            return true;
        else
            return false;
    }

    function SKVATCheckDigit(vatnumber) {

        // Checks the check digits of a Slovakian VAT number.

        // Check that the modulus of the whole VAT number is 0 - else error
        if (Number(vatnumber % 11) == 0)
            return true;
        else
            return false;
    }

    return checkVATNumber;
})();