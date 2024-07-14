/* @odoo-module */
import { parseEmail } from "@mail/js/utils";

/**
 * splits the string and find all the invalid emails from it.
 *
 * @param {string}
 * @return {object}
 */
function findInvalidEmailFromText(emailStr){
    const emailList = emailStr.split('\n');
    const invalidEmails = emailList.filter(email => email !== '' && !parseEmail(email.trim())[1]);
    const emailInfo = {
        'invalidEmails': invalidEmails,
        'emailList': emailList,
    }
    return emailInfo
}

export {
    findInvalidEmailFromText
};
