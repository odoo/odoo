/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            SnailmailErrorComponent
        [Model/fields]
            snailmailErrorView
        [Model/elements]
            root
                title
                separator
                creditConditional
                    contentCredit
                    creditsBuyContainer
                        creditBuy
                            creditBuyIcon
                            creditBuyLabel
                trialConditional
                    contentTrial
                    trialBuyContainer
                        trialBuy
                            trialBuyIcon
                            trialBuyLabel
                contentPrice
                contentError
                separator
                buttons
                    resendLetterButton
                    cancelLetterButton
                    closeButton
`;
