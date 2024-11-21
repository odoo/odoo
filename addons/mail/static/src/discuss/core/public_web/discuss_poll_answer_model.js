import { Record } from "@mail/model/record";

export class DiscussPollAnswerModel extends Record {
    static id = "id";
    static _name = "discuss.poll.answer";

    /** @type {number} */
    id;
    poll_id = Record.one("discuss.poll");
    /** @type {string} */
    text;
    voting_partner_ids = Record.many("Persona");
    percent_votes = 0;

    get selectedBySelf() {
        return this.store.self.in(this.voting_partner_ids);
    }

    /**
     * Returns the percentage of votes for this answer, rounded based on the
     * largest remainders method.
     *
     * @returns {number}
     */
    get percentage() {
        const percentageData = this.poll_id.answer_ids
            .map((answer) => {
                const exactPercentage =
                    (100 * answer.voting_partner_ids.length) / this.poll_id.number_of_votes || 0;
                const integerPart = Math.floor(exactPercentage);
                const decimalPart = integerPart === 0 ? 0 : exactPercentage % integerPart;
                return { answerId: answer.id, integerPart, decimalPart };
            })
            .sort((a, b) => {
                if (a.integerPart !== b.integerPart) {
                    return b.integerPart - a.integerPart;
                }
                if (a.decimalPart !== b.decimalPart) {
                    return b.decimalPart - a.decimalPart;
                }
                return a.answerId - b.answerId;
            });
        let total = percentageData.reduce((sum, data) => sum + data.integerPart, 0);
        let exit = false;
        while (total < 100 && !exit) {
            for (let i = 0; i < percentageData.length && total < 100; i += 1) {
                if (percentageData[i].integerPart === percentageData[i + 1]?.integerPart) {
                    exit = true;
                    break; // Do not skew the percentage when it's a tie.
                }
                percentageData[i].integerPart += 1;
                total += 1;
            }
        }
        return percentageData.find(({ answerId }) => answerId === this.id).integerPart;
    }
}
DiscussPollAnswerModel.register();
