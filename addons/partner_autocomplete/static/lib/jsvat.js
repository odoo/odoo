/*==================================================================================================

Application:  Utility Function
Author:       John Gardner, MFG Labs, Akkroo Solutions Ltd
Version:      V1.16-8

function checkVATNumber (myVATNumber, countryCode)

This function checks the value of the parameter for a valid European VAT number and a given country code.

Parameters:
 - myVATNumber: VAT number be checked.
 - countryCode: (optional) two letters country code, to be matched against the VAt number.

Return:
 - number: the re-formatted VAT number.
 - valid_vat: if the number is valid in itself.
 - valid_country: if the country of the VAT number matches the optional countryCode param.

Example call:

  var checkVATObject = checkVATNumber(myVATNumber, countryCode);

  if (checkVATObject.valid_country)
      alert ("VAT Number does match the country code")
  else
      alert ("VAT number doesn't match the country code");

  if (checkVATObject.valid_vat)
      alert ("VAT number has a valid format")
  else
      alert ("VAT number has invalid format");

Other examples:

checkVATNumber("FR 37 50 999 58 09")
Object {valid_country: true, valid_vat: true, number: "FR37509995809"}

checkVATNumber("FR 37 50 999 58 09", "FR")
Object {valid_country: true, valid_vat: true, number: "FR37509995809"}

checkVATNumber("FR 37 50 999 58 09", "XX")
Object {valid_country: false, valid_vat: true, number: "FR37509995809"}

checkVATNumber("XX 37 50 999 58 09", "XX")
Object {valid_country: false, valid_vat: false, number: "XX37509995809"}

checkVATNumber("XX 37 50 999 58 09", "FR")
Object {valid_country: true, valid_vat: false, number: "XX37509995809"}

---------------------------------------------------------------------------------------------------*/

function checkVATNumber (toCheck, country_code) {

    // Array holds the regular expressions for the valid VAT number
    var vatexp = new Array ();

    // To change the default country (e.g. from the UK to Germany - DE):
    //    1.  Change the country code in the defCCode variable below to "DE".
    //    2.  Remove the question mark from the regular expressions associated with the UK VAT number:
    //        i.e. "(GB)?" -> "(GB)"
    //    3.  Add a question mark into the regular expression associated with Germany's number
    //        following the country code: i.e. "(DE)" -> "(DE)?"

    var defCCode = "GB";

    if (country_code) country_code = country_code.replace(/\s*/gi,"").toUpperCase();

    toCheck = toCheck.replace(/\s*/gi,"");

    // Note - VAT codes without the "**" in the comment do not have check digit checking.

    vatexp.push (/^(AT)U(\d{8})$/);                           //** Austria
    vatexp.push (/^(BE)(0?\d{9})$/);                          //** Belgium
    vatexp.push (/^(BG)(\d{9,10})$/);                         //** Bulgaria
    vatexp.push (/^(CH)E(\d{9})((MWST)|(IVA)|(TVA))/);        // Switzerland
    vatexp.push (/^(CY)([0-5|9]\d{7}[A-Z])$/);                //** Cyprus
    vatexp.push (/^(CZ)(\d{8,10})(\d{3})?$/);                 //** Czech Republic
    vatexp.push (/^(DE)([1-9]\d{8})$/);                       //** Germany
    vatexp.push (/^(DK)((\d{8}))$/);                          //** Denmark
    vatexp.push (/^(EE)(10\d{7})$/);                          //** Estonia
    vatexp.push (/^(EL)(\d{9})$/);                            //** Greece
    vatexp.push (/^(ES)([A-Z]\d{8})$/);                       //** Spain (National juridical entities)
    vatexp.push (/^(ES)([A-H|N-S|W]\d{7}[A-J])$/);            //** Spain (Other juridical entities)
    vatexp.push (/^(ES)([0-9|Y|Z]\d{7}[A-Z])$/);              //** Spain (Personal entities type 1)
    vatexp.push (/^(ES)([K|L|M|X]\d{7}[A-Z])$/);              //** Spain (Personal entities type 2)
    vatexp.push (/^(EU)(\d{9})$/);                            //** EU-type
    vatexp.push (/^(FI)(\d{8})$/);                            //** Finland
    vatexp.push (/^(FR)(\d{11})$/);                           //** France (1)
    vatexp.push (/^(FR)[(A-H)|(J-N)|(P-Z)]\d{10}$/);          // France (2)
    vatexp.push (/^(FR)\d[(A-H)|(J-N)|(P-Z)]\d{9}$/);         // France (3)
    vatexp.push (/^(FR)[(A-H)|(J-N)|(P-Z)]{2}\d{9}$/);        // France (4)
    vatexp.push (/^(GB)?(\d{9})$/);                           //** UK (Standard)
    vatexp.push (/^(GB)?(\d{12})$/);                          //** UK (Branches)
    vatexp.push (/^(GB)?(GD\d{3})$/);                         //** UK (Government)
    vatexp.push (/^(GB)?(HA\d{3})$/);                         //** UK (Health authority)
    vatexp.push (/^(GR)(\d{8,9})$/);                          //** Greece
    vatexp.push (/^(HR)(\d{11})$/);                           //** Croatia
    vatexp.push (/^(HU)(\d{8})$/);                            //** Hungary
    vatexp.push (/^(IE)(\d{7}[A-W])$/);                       //** Ireland (1)
    vatexp.push (/^(IE)([7-9][A-Z\*\+)]\d{5}[A-W])$/);        //** Ireland (2)
    vatexp.push (/^(IT)(\d{11})$/);                           //** Italy
    vatexp.push (/^(LV)(\d{11})$/);                           //** Latvia
    vatexp.push (/^(LT)(\d{9}|\d{12})$/);                     //** Lithunia
    vatexp.push (/^(LU)(\d{8})$/);                            //** Luxembourg
    vatexp.push (/^(MT)([1-9]\d{7})$/);                       //** Malta
    vatexp.push (/^(NL)(\d{9})B\d{2}$/);                      //** Netherlands
    vatexp.push (/^(PL)(\d{10})$/);                           //** Poland
    vatexp.push (/^(PT)(\d{9})$/);                            //** Portugal
    vatexp.push (/^(RO)([1-9]\d{1,9})$/);                     //** Romania
    vatexp.push (/^(SI)([1-9]\d{7})$/);                       //** Slovenia
    vatexp.push (/^(SK)([1-9]\d[(2-4)|(6-9)]\d{7})$/);        //** Slovakia Republic
    vatexp.push (/^(SE)(\d{10}01)$/);                         //** Sweden

    // Load up the string to check
    var VATNumber = toCheck.toUpperCase();

    // Remove spaces from the VAT number to help validation
    var chars = [" ","-",",","."];
    for ( var i=0; i<chars.length; i++) {
        while (VATNumber.indexOf(chars[i])!= -1) {
            VATNumber = VATNumber.slice (0,VATNumber.indexOf(chars[i])) + VATNumber.slice (VATNumber.indexOf(chars[i])+1);
        }
    }

    var valid = false;
    var valid_country = false;
    if (country_code) {
        switch (country_code) {
            case "AT":
                if (country_code == "AT") {
                    valid_country = true;
                }
                break;
            case "BE":
                if (country_code == "BE") {
                    valid_country = true;
                }
                break;
            case "BG":
                if (country_code == "BG") {
                    valid_country = true;
                }
                break;
            case "CH":
                if (country_code == "CH") {
                    valid_country = true;
                }
            case "CY":
                if (country_code == "CY") {
                    valid_country = true;
                }
                break;
            case "CZ":
                if (country_code == "CZ") {
                    valid_country = true;
                }
                break;
            case "DE":
                if (country_code == "DE") {
                    valid_country = true;
                }
                break;
            case "DK":
                if (country_code == "DK") {
                    valid_country = true;
                }
                break;
            case "EE":
                if (country_code == "EE") {
                    valid_country = true;
                }
                break;
            case "EL":
                if (country_code == "GR") {
                    valid_country = true;
                }
                break;
            case "ES":
                if (country_code == "ES") {
                    valid_country = true;
                }
                break;
            case "EU":
                if (country_code == "EU") {
                    valid_country = true;
                }
                break;
            case "FI":
                if (country_code == "FI") {
                    valid_country = true;
                }
                break;
            case "FR":
                if (
                    country_code == "FR"
                    || country_code == "GF"
                    || country_code == "PF"
                    || country_code == "TF") {
                    valid_country = true;
                }
                break;
            case "GB":
                if (country_code == "GB") {
                    valid_country = true;
                }
                break;
            case "GR":
                if (country_code == "GR") {
                    valid_country = true;
                }
                break;
            case "HR":
                if (country_code == "HR") {
                    valid_country = true;
                }
                break;
            case "HU":
                if (country_code == "HU") {
                    valid_country = true;
                }
                break;
            case "IE":
                if (country_code == "IE") {
                    valid_country = true;
                }
                break;
            case "IT":
                if (country_code == "IT") {
                    valid_country = true;
                }
                break;
            case "LT":
                if (country_code == "LT") {
                    valid_country = true;
                }
                break;
            case "LU":
                if (country_code == "LU") {
                    valid_country = true;
                }
                break;
            case "LV":
                if (country_code == "LV") {
                    valid_country = true;
                }
                break;
            case "MT":
                if (country_code == "MT") {
                    valid_country = true;
                }
                break;
            case "NL":
                if (country_code == "NL") {
                    valid_country = true;
                }
                break;
            case "PL":
                if (country_code == "PL") {
                    valid_country = true;
                }
                break;
            case "PT":
                if (country_code == "PT") {
                    valid_country = true;
                }
                break;
            case "RO":
                if (country_code == "RO") {
                    valid_country = true;
                }
                break;
            case "SE":
                if (country_code == "SE") {
                    valid_country = true;
                }
                break;
            case "SI":
                if (country_code == "SI") {
                    valid_country = true;
                }
                break;
            case "SK":
                if (country_code == "SK") {
                    valid_country = true;
                }
                break;
            default:
                valid_country = false;
        }
    }

    // Check the string against the types of VAT numbers
    for (i=0; i<vatexp.length; i++) {
        if (vatexp[i].test(VATNumber)) {

            var cCode = RegExp.$1;                             // Isolate country code
            var cNumber = RegExp.$2;                           // Isolate the number
            if (cCode.length == 0) cCode = defCCode;           // Set up default country code

            // Now look at the check digits for those countries we know about.
            switch (cCode) {
                case "AT":
                    valid = ATVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "AT");
                    break;
                case "BE":
                    valid = BEVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "BE");
                    break;
                case "BG":
                    valid = BGVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "BG");
                    break;
                case "CH":
                    valid = CHVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "CH");
                    break;
                case "CY":
                    valid = CYVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "CY");
                    break;
                case "CZ":
                    valid = CZVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "CZ");
                    break;
                case "DE":
                    valid = DEVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "DE");
                    break;
                case "DK":
                    valid = DKVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "DK");
                    break;
                case "EE":
                    valid = EEVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "EE");
                    break;
                case "EL":
                    valid = ELVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "GR");
                    break;
                case "ES":
                    valid = ESVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "ES");
                    break;
                case "EU":
                    valid = EUVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "EU");
                    break;
                case "FI":
                    valid = FIVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "FI");
                    break;
                case "FR":
                    valid = FRVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "FR" || country_code == "GF"|| country_code == "PF" || country_code == "TF");
                    break;
                case "GB":
                    valid = UKVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "GB");
                    break;
                case "GR":
                    valid = ELVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "GR");
                    break;
                case "HR":
                    valid = HRVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "HR");
                    break;
                case "HU":
                    valid = HUVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "HU");
                    break;
                case "IE":
                    valid = IEVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "IE");
                    break;
                case "IT":
                    valid = ITVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "IT");
                    break;
                case "LT":
                    valid = LTVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "LT");
                    break;
                case "LU":
                    valid = LUVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "LU");
                    break;
                case "LV":
                    valid = LVVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "LV");
                    break;
                case "MT":
                    valid = MTVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "MT");
                    break;
                case "NL":
                    valid = NLVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "NL");
                    break;
                case "PL":
                    valid = PLVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "PL");
                    break;
                case "PT":
                    valid = PTVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "PT");
                    break;
                case "RO":
                    valid = ROVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "RO");
                    break;
                case "SE":
                    valid = SEVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "SE");
                    break;
                case "SI":
                    valid = SIVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "SI");
                    break;
                case "SK":
                    valid = SKVATCheckDigit (cNumber);
                    valid_country = (!country_code || country_code == "SK");
                    break;
                default:
                    if (country_code) {
                        valid = false;
                    } else {
                        valid = true;
                    }
                    break;
            }

            // We have found that the number is valid - break from loop
            break;
        }
    }

    // Return with either an error or the reformatted VAT number
    return {
        valid_country: valid_country,
        valid_vat: valid,
        number: VATNumber
    };
}

function ATVATCheckDigit (vatnumber) {

    // Checks the check digits of an Austrian VAT number.

    var total = 0;
    var multipliers = [1,2,1,2,1,2,1];
    var temp = 0;

    // Extract the next digit and multiply by the appropriate multiplier.
    for (var i = 0; i < 7; i++) {
        temp = Number(vatnumber.charAt(i)) * multipliers[i];
        if (temp > 9)
            total = total + Math.floor(temp/10) + temp%10
        else
            total = total + temp;
    }

    // Establish check digit.
    total = 10 - (total+4) % 10;
    if (total == 10) total = 0;

    // Compare it with the last character of the VAT number. If it is the same,
    // then it's a valid check digit.
    if (total == vatnumber.slice (7,8))
        return true
    else
        return false;
}

function BEVATCheckDigit (vatnumber) {

    // Checks the check digits of a Belgium VAT number.

    // Nine digit numbers have a 0 inserted at the front.
    if (vatnumber.length == 9) vatnumber = "0" + vatnumber;

    if (vatnumber.slice(1,2) == 0) return false;

    // Modulus 97 check on last nine digits
    if (97 - vatnumber.slice (0,8) % 97 == vatnumber.slice (8,10))
        return true
    else
        return false;
}

function BGVATCheckDigit (vatnumber) {

    // Checks the check digits of a Bulgarian VAT number.

    if (vatnumber.length == 9) {

        // Check the check digit of 9 digit Bulgarian VAT numbers.
        var total = 0;

        // First try to calculate the check digit using the first multipliers
        var temp = 0;
        for (var i = 0; i < 8; i++) temp = temp + Number(vatnumber.charAt(i)) * (i+1);

        // See if we have a check digit yet
        total = temp % 11;
        if (total != 10) {
            if (total == vatnumber.slice (8))
                return true
            else
                return false;
        }

        // We got a modulus of 10 before so we have to keep going. Calculate the new check digit using the
        // different multipliers
        var temp = 0;
        for (var i = 0; i < 8; i++) temp = temp + Number(vatnumber.charAt(i)) * (i+3);

        // See if we have a check digit yet. If we still have a modulus of 10, set it to 0.
        total = temp % 11;
        if (total == 10) total = 0;
        if (total == vatnumber.slice (8))
            return true
        else
            return false;
    }

    // 10 digit VAT code - see if it relates to a standard physical person
    if ((/^\d\d[0-5]\d[0-3]\d\d{4}$/).test(vatnumber)) {

        // Check month
        var month = Number(vatnumber.slice(2,4));
        if ((month > 0 && month < 13) || (month > 20 & month < 33)) {

            // Extract the next digit and multiply by the counter.
            var multipliers = [2,4,8,5,10,9,7,3,6];
            var total = 0;
            for (var i = 0; i < 9; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

            // Establish check digit.
            total = total % 11;
            if (total == 10) total = 0;

            // Check to see if the check digit given is correct, If not, try next type of person
            if (total == vatnumber.substr (9,1)) return true;
        }
    }

    // It doesn't relate to a standard physical person - see if it relates to a foreigner.

    // Extract the next digit and multiply by the counter.
    var multipliers = [21,19,17,13,11,9,7,3,1];
    var total = 0;
    for (var i = 0; i < 9; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Check to see if the check digit given is correct, If not, try next type of person
    if (total % 10 == vatnumber.substr (9,1)) return true;

    // Finally, if not yet identified, see if it conforms to a miscellaneous VAT number

    // Extract the next digit and multiply by the counter.
    var multipliers = [4,3,2,7,6,5,4,3,2];
    var total = 0;
    for (var i = 0; i < 9; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digit.
    total = 11 - total % 11;
    if (total == 10) return false;
    if (total == 11) total = 0;

    // Check to see if the check digit given is correct, If not, we have an error with the VAT number
    if (total == vatnumber.substr (9,1))
        return true;
    else
        return false;
}

function CHVATCheckDigit (vatnumber) {

    // Checks the check digits of a Swiss VAT number.

    var total = 0;
    var multipliers = [5,4,3,2,7,6,5,4];

    // Extract the next digit and multiply by the appropriate multiplier.
    for (var i = 0; i < 8; i++) {
        total = total + Number(vatnumber.charAt(i)) * multipliers[i];
    }

    // Establish check digit.
    total = (11 - (total % 11)) % 11;

    // Compare it with the last character of the VAT number. If it is the same,
    // then it's a valid check digit.
    if (total == vatnumber.slice (8,9))
        return true
    else
        return false;
}

function CYVATCheckDigit (vatnumber) {

    // Checks the check digits of a Cypriot VAT number.

    // Not allowed to start with '12'
    if (Number(vatnumber.slice(0,2) == 12)) return false;

    // Extract the next digit and multiply by the counter.
    var total = 0;
    for (var i = 0; i < 8; i++) {
        var temp = Number(vatnumber.charAt(i));
        if (i % 2 == 0) {
            switch (temp) {
                case 0: temp = 1; break;
                case 1: temp = 0; break;
                case 2: temp = 5; break;
                case 3: temp = 7; break;
                case 4: temp = 9; break;
                default: temp = temp*2 + 3;
            }
        }
        total = total + temp;
    }

    // Establish check digit using modulus 26, and translate to char. equivalent.
    total = total % 26;
    total = String.fromCharCode(total+65);

    // Check to see if the check digit given is correct
    if (total == vatnumber.substr (8,1))
        return true
    else
        return false;
}

function CZVATCheckDigit (vatnumber) {

    // Checks the check digits of a Czech Republic VAT number.

    var total = 0;
    var multipliers = [8,7,6,5,4,3,2];

    var czexp = new Array ();
    czexp[0] = (/^\d{8}$/);
    czexp[1] = (/^[0-5][0-9][0|1|5|6]\d[0-3]\d\d{3}$/);
    czexp[2] = (/^6\d{8}$/);
    czexp[3] = (/^\d{2}[0-3|5-8]\d[0-3]\d\d{4}$/);
    var i = 0;

    // Legal entities
    if (czexp[0].test(vatnumber)) {

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digit.
        total = 11 - total % 11;
        if (total == 10) total = 0;
        if (total == 11) total = 1;

        // Compare it with the last character of the VAT number. If it is the same,
        // then it's a valid check digit.
        if (total == vatnumber.slice (7,8))
            return true
        else
            return false;
    }

    // Individuals type 1
    else if (czexp[1].test(vatnumber)) {
        if (temp = Number(vatnumber.slice(0,2)) > 53) return false;
        return true;
    }

    // Individuals type 2
    else if (czexp[2].test(vatnumber)) {

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i+1)) * multipliers[i];

        // Establish check digit.
        total = 11 - total % 11;
        if (total == 10) total = 0;
        if (total == 11) total = 1;

        // Convert calculated check digit according to a lookup table;
        var lookup  = [8,7,6,5,4,3,2,1,0,9,10];
        if (lookup[total-1] == vatnumber.slice (8,9))
            return true
        else
            return false;
    }

    // Individuals type 3
    else if (czexp[3].test(vatnumber)) {
        var temp = Number(vatnumber.slice(0,2)) + Number(vatnumber.slice(2,4)) + Number(vatnumber.slice(4,6)) + Number(vatnumber.slice(6,8)) + Number(vatnumber.slice(8));
        if (temp % 11 == 0 && Number(vatnumber) % 11 == 0)
            return true
        else
            return false;
    }

    // else error
    return false;
}

function DEVATCheckDigit (vatnumber) {

    // Checks the check digits of a German VAT number.

    var product = 10;
    var sum = 0;
    var checkdigit = 0;
    for (var i = 0; i < 8; i++) {

        // Extract the next digit and implement peculiar algorithm!.
        sum = (Number(vatnumber.charAt(i)) + product) % 10;
        if (sum == 0) {sum = 10};
        product = (2 * sum) % 11;
    }

    // Establish check digit.
    if (11 - product == 10) {checkdigit = 0} else {checkdigit = 11 - product};

    // Compare it with the last two characters of the VAT number. If the same, then it is a valid
    // check digit.
    if (checkdigit == vatnumber.slice (8,9))
        return true
    else
        return false;
}

function DKVATCheckDigit (vatnumber) {

    // Checks the check digits of a Danish VAT number.

    var total = 0;
    var multipliers = [2,7,6,5,4,3,2,1];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digit.
    total = total % 11;

    // The remainder should be 0 for it to be valid..
    if (total == 0)
        return true
    else
        return false;
}

function EEVATCheckDigit (vatnumber) {

    // Checks the check digits of an Estonian VAT number.

    var total = 0;
    var multipliers = [3,7,1,3,7,1,3,7];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digits using modulus 10.
    total = 10 - total % 10;
    if (total == 10) total = 0;

    // Compare it with the last character of the VAT number. If it is the same,
    // then it's a valid check digit.
    if (total == vatnumber.slice (8,9))
        return true
    else
        return false;
}

function ELVATCheckDigit (vatnumber) {

    // Checks the check digits of a Greek VAT number.

    var total = 0;
    var multipliers = [256,128,64,32,16,8,4,2];

    //eight character numbers should be prefixed with an 0.
    if (vatnumber.length == 8) {vatnumber = "0" + vatnumber};

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digit.
    total = total % 11;
    if (total > 9) {total = 0;};

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (8,9))
        return true
    else
        return false;
}

function ESVATCheckDigit (vatnumber) {

    // Checks the check digits of a Spanish VAT number.

    var total = 0;
    var temp = 0;
    var multipliers = [2,1,2,1,2,1,2];
    var esexp = new Array ();
    esexp[0] = (/^[A-H|J|U|V]\d{8}$/);
    esexp[1] = (/^[A-H|N-S|W]\d{7}[A-J]$/);
    esexp[2] = (/^[0-9|Y|Z]\d{7}[A-Z]$/);
    esexp[3] = (/^[K|L|M|X]\d{7}[A-Z]$/);
    var i = 0;

    // National juridical entities
    if (esexp[0].test(vatnumber)) {

        // Extract the next digit and multiply by the counter.
        for (i = 0; i < 7; i++) {
            temp = Number(vatnumber.charAt(i+1)) * multipliers[i];
            if (temp > 9)
                total = total + Math.floor(temp/10) + temp%10
            else
                total = total + temp;
        }
        // Now calculate the check digit itself.
        total = 10 - total % 10;
        if (total == 10) {total = 0;}

        // Compare it with the last character of the VAT number. If it is the same, then it's a valid
        // check digit.
        if (total == vatnumber.slice (8,9))
            return true
        else
            return false;
    }

    // Juridical entities other than national ones
    else if (esexp[1].test(vatnumber)) {

        // Extract the next digit and multiply by the counter.
        for (i = 0; i < 7; i++) {
            temp = Number(vatnumber.charAt(i+1)) * multipliers[i];
            if (temp > 9)
                total = total + Math.floor(temp/10) + temp%10
            else
                total = total + temp;
        }

        // Now calculate the check digit itself.
        total = 10 - total % 10;
        total = String.fromCharCode(total+64);

        // Compare it with the last character of the VAT number. If it is the same, then it's a valid
        // check digit.
        if (total == vatnumber.slice (8,9))
            return true
        else
            return false;
    }

    // Personal number (NIF) (starting with numeric of Y or Z)
    else if (esexp[2].test(vatnumber)) {
        var tempnumber = vatnumber;
        if (tempnumber.substring(0,1) == 'Y') tempnumber = tempnumber.replace (/Y/, "1");
        if (tempnumber.substring(0,1) == 'Z') tempnumber = tempnumber.replace (/Z/, "2");
        return tempnumber.charAt(8) == 'TRWAGMYFPDXBNJZSQVHLCKE'.charAt(Number(tempnumber.substring(0,8)) % 23);
    }

    // Personal number (NIF) (starting with K, L, M, or X)
    else if (esexp[3].test(vatnumber)) {
        return vatnumber.charAt(8) == 'TRWAGMYFPDXBNJZSQVHLCKE'.charAt(Number(vatnumber.substring(1,8)) % 23);
    }

    else return false;
}

function EUVATCheckDigit (vatnumber) {

    // We know litle about EU numbers apart from the fact that the first 3 digits represent the
    // country, and that there are nine digits in total.
    return true;
}

function FIVATCheckDigit (vatnumber) {

    // Checks the check digits of a Finnish VAT number.

    var total = 0;
    var multipliers = [7,9,10,5,8,4,2];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digit.
    total = 11 - total % 11;
    if (total > 9) {total = 0;};

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (7,8))
        return true
    else
        return false;
}

function FRVATCheckDigit (vatnumber) {

    // Checks the check digits of a French VAT number.

    if (!(/^\d{11}$/).test(vatnumber)) return false;

    // Extract the last nine digits as an integer.
    var total = vatnumber.substring(2);

    // Establish check digit.
    total = (total*100+12) % 97;

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (0,2))
        return true
    else
        return false;
}

function HRVATCheckDigit (vatnumber) {

    // Checks the check digits of a Croatian VAT number using ISO 7064, MOD 11-10 for check digit.

    var product = 10;
    var sum = 0;
    var checkdigit = 0;

    for (var i = 0; i < 10; i++) {

        // Extract the next digit and implement the algorithm
        sum = (Number(vatnumber.charAt(i)) + product) % 10;
        if (sum == 0) {sum = 10};
        product = (2 * sum) % 11;
    }

    // Now check that we have the right check digit
    if ((product + vatnumber.slice (10,11)*1) % 10== 1)
        return true
    else
        return false;
}

function HUVATCheckDigit (vatnumber) {

    // Checks the check digits of a Hungarian VAT number.

    var total = 0;
    var multipliers = [9,7,3,1,9,7,3];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digit.
    total = 10 - total % 10;
    if (total == 10) total = 0;

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (7,8))
        return true
    else
        return false;
}

function IEVATCheckDigit (vatnumber) {

    // Checks the check digits of an Irish VAT number.

    var total = 0;
    var multipliers = [8,7,6,5,4,3,2];

    // If the code is in the old format, we need to convert it to the new.
    if (/^\d[A-Z\*\+]/.test(vatnumber)) vatnumber = "0" + vatnumber.substring(2,7) + vatnumber.substring(0,1) + vatnumber.substring(7,8);

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digit using modulus 23, and translate to char. equivalent.
    total = total % 23;
    if (total == 0)
        total = "W"
    else
        total = String.fromCharCode(total+64);

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (7,8))
        return true
    else
        return false;
}

function ITVATCheckDigit (vatnumber) {

    // Checks the check digits of an Italian VAT number.

    var total = 0;
    var multipliers = [1,2,1,2,1,2,1,2,1,2];
    var temp;

    // The last three digits are the issuing office, and cannot exceed more 201, unless 999 or 8888
    if (Number(vatnumber.slice(0,7))==0) return false;
    temp=Number(vatnumber.slice(7,10));
    if ((temp<1) || (temp>201) && temp != 999 && temp != 888) return false;

    // Extract the next digit and multiply by the appropriate
    for (var i = 0; i < 10; i++) {
        temp = Number(vatnumber.charAt(i)) * multipliers[i];
        if (temp > 9)
            total = total + Math.floor(temp/10) + temp%10
        else
            total = total + temp;
    }

    // Establish check digit.
    total = 10 - total % 10;
    if (total > 9) {total = 0;};

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (10,11))
        return true
    else
        return false;
}

function LTVATCheckDigit (vatnumber) {

    // Checks the check digits of a Lithuanian VAT number.

    // 9 character VAT numbers are for legal persons
    if (vatnumber.length == 9) {

        // 8th character must be one
        if (!(/^\d{7}1/).test(vatnumber)) return false;

        // Extract the next digit and multiply by the counter+1.
        var total = 0;
        for (var i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * (i+1);

        // Can have a double check digit calculation!
        if (total % 11 == 10) {
            var multipliers = [3,4,5,6,7,8,9,1];
            total = 0;
            for (i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];
        }

        // Establish check digit.
        total = total % 11;
        if (total == 10) {total = 0;};

        // Compare it with the last character of the VAT number. If it is the same,
        // then it's a valid check digit.
        if (total == vatnumber.slice (8,9))
            return true
        else
            return false;
    }

    // 12 character VAT numbers are for temporarily registered taxpayers
    else {

        // 11th character must be one
        if (!(/^\d{10}1/).test(vatnumber)) return false;

        // Extract the next digit and multiply by the counter+1.
        var total = 0;
        var multipliers = [1,2,3,4,5,6,7,8,9,1,2];
        for (var i = 0; i < 11; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

        // Can have a double check digit calculation!
        if (total % 11 == 10) {
            var multipliers = [3,4,5,6,7,8,9,1,2,3,4];
            total = 0;
            for (i = 0; i < 11; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];
        }

        // Establish check digit.
        total = total % 11;
        if (total == 10) {total = 0;};

        // Compare it with the last character of the VAT number. If it is the same, then it's a valid
        // check digit.
        if (total == vatnumber.slice (11,12))
            return true
        else
            return false;
    }
}

function LUVATCheckDigit (vatnumber) {

    // Checks the check digits of a Luxembourg VAT number.

    if (vatnumber.slice (0,6) % 89 == vatnumber.slice (6,8))
        return true
    else
        return false;
}

function LVVATCheckDigit (vatnumber) {

    // Checks the check digits of a Latvian VAT number.

    // Differentiate between legal entities and natural bodies. For the latter we simplly check that
    // the first six digits correspond to valid DDMMYY dates.
    if ((/^[0-3]/).test(vatnumber)) {
        if ((/^[0-3][0-9][0-1][0-9]/).test(vatnumber) )
            return true
        else
            return false;
    }

    else {

        var total = 0;
        var multipliers = [9,1,4,8,3,10,2,5,7,6];

        // Extract the next digit and multiply by the counter.
        for (var i = 0; i < 10; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

        // Establish check digits by getting modulus 11.
        if (total%11 == 4 && vatnumber[0] ==9) total = total - 45;
        if (total%11 == 4)
            total = 4 - total%11
        else if (total%11 > 4)
            total = 14 - total%11
        else if (total%11 < 4)
            total = 3 - total%11;

        // Compare it with the last character of the VAT number. If it is the same,
        // then it's a valid check digit.
        if (total == vatnumber.slice (10,11))
            return true
        else
            return false;
    }
}

function MTVATCheckDigit (vatnumber) {

    // Checks the check digits of a Maltese VAT number.

    var total = 0;
    var multipliers = [3,4,6,7,8,9];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 6; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digits by getting modulus 37.
    total = 37 - total % 37;

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (6,8) * 1)
        return true
    else
        return false;
}

function NLVATCheckDigit (vatnumber) {

    // Checks the check digits of a Dutch VAT number.

    var total = 0;
    var multipliers = [9,8,7,6,5,4,3,2];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digits by getting modulus 11.
    total = total % 11;
    if (total > 9) {total = 0;};

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (8,9))
        return true
    else
        return false;
}

function PLVATCheckDigit (vatnumber) {

    // Checks the check digits of a Polish VAT number.

    var total = 0;
    var multipliers = [6,5,7,2,3,4,5,6,7];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 9; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digits subtracting modulus 11 from 11.
    total = total % 11;
    if (total > 9) {total = 0;};

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (9,10))
        return true
    else
        return false;
}

function PTVATCheckDigit (vatnumber) {

    // Checks the check digits of a Portugese VAT number.

    var total = 0;
    var multipliers = [9,8,7,6,5,4,3,2];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 8; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digits subtracting modulus 11 from 11.
    total = 11 - total % 11;
    if (total > 9) {total = 0;};

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (8,9))
        return true
    else
        return false;
}

function ROVATCheckDigit (vatnumber) {

    // Checks the check digits of a Romanian VAT number.

    var multipliers = [7,5,3,2,1,7,5,3,2];

    // Extract the next digit and multiply by the counter.
    var VATlen = vatnumber.length;
    multipliers = multipliers.slice (10-VATlen);
    var total = 0;
    for (var i = 0; i < vatnumber.length-1; i++) {
        total = total + Number(vatnumber.charAt(i)) * multipliers[i];
    }

    // Establish check digits by getting modulus 11.
    total = (10 * total) % 11;
    if (total == 10) total = 0;

    // Compare it with the last character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (total == vatnumber.slice (vatnumber.length-1, vatnumber.length))
        return true
    else
        return false;
}

function SEVATCheckDigit (vatnumber) {

    // Calculate R where R = R1 + R3 + R5 + R7 + R9, and Ri = INT(Ci/5) + (Ci*2) modulo 10
    var R = 0;
    var digit;
    for (var i = 0; i < 9; i=i+2) {
        digit = Number(vatnumber.charAt(i));
        R = R + Math.floor(digit / 5)  + ((digit * 2) % 10);
    }

    // Calculate S where S = C2 + C4 + C6 + C8
    var S = 0;
    for (var i = 1; i < 9; i=i+2) S = S + Number(vatnumber.charAt(i));

    // Calculate the Check Digit
    var cd = (10 - (R + S) % 10) % 10;

    // Compare it with the 10th character of the VAT number. If it is the same, then it's a valid
    // check digit.
    if (cd == vatnumber.slice (9,10))
        return true
    else
        return false;
}

function SIVATCheckDigit (vatnumber) {

    // Checks the check digits of a Slovenian VAT number.

    var total = 0;
    var multipliers = [8,7,6,5,4,3,2];

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Establish check digits using modulus 11
    total = 11 - total % 11;
    if (total == 10) {total = 0;};

    // Compare the number with the last character of the VAT number. If it is the
    // same, then it's a valid check digit.
    if (total != 11 && total == vatnumber.slice (7,8))
        return true
    else
        return false;
}

function SKVATCheckDigit (vatnumber) {

    // Checks the check digits of a Slovakian VAT number.

    // Check that the modulus of the whole VAT nnumber is 0 - else error
    if (Number(vatnumber % 11) == 0)
        return true
    else
        return false;
}

function UKVATCheckDigit (vatnumber) {

    // Checks the check digits of a UK VAT number.

    var multipliers = [8,7,6,5,4,3,2];

    // Government departments
    if (vatnumber.substr(0,2) == 'GD') {
        if (vatnumber.substr(2,3) < 500)
            return true
        else
            return false;
    }

    // Health authorities
    if (vatnumber.substr(0,2) == 'HA') {
        if (vatnumber.substr(2,3) > 499)
            return true
        else
            return false;
    }

    // Standard and commercial numbers
    var total = 0;

    // 0 VAT numbers disallowed!
    if (Number(vatnumber.slice(0)) == 0) return false;

    // Check range is OK for modulus 97 calculation
    var no = Number(vatnumber.slice(0,7));

    // Extract the next digit and multiply by the counter.
    for (var i = 0; i < 7; i++) total = total + Number(vatnumber.charAt(i)) * multipliers[i];

    // Old numbers use a simple 97 modulus, but new numbers use an adaptation of that (less 55). Our
    // VAT number could use either system, so we check it against both.

    // Establish check digits by subtracting 97 from total until negative.
    var cd = total;
    while (cd > 0) {cd = cd - 97;}

    // Get the absolute value and compare it with the last two characters of the VAT number. If the
    // same, then it is a valid traditional check digit. However, even then the number must fit within
    // certain specified ranges.
    cd = Math.abs(cd);
    if (cd == vatnumber.slice (7,9) && no < 9990001 && (no < 100000 || no > 999999) && (no < 9490001 || no > 9700000)) return true;

    // Now try the new method by subtracting 55 from the check digit if we can - else add 42
    if (cd >= 55)
        cd = cd - 55
    else
        cd = cd + 42;
    if (cd == vatnumber.slice (7,9) && no > 1000000)
        return true;
    else
        return false;
}
