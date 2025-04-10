import { registry } from "@web/core/registry";
import { getDataFromEl } from "@web/public/utils";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { markup } from "@odoo/owl";

// TODO: check naming convention for services
const quizService = {
    dependencies: [],
    /**
     * Extract data from exiting DOM rendered server-side, to have the list of questions with their
     * relative answers.
     * This method should return the same format as /slide/quiz/get controller.
     *
     * @return {Array<Object>} list of questions with answers
     */
    extractQuestionsAndAnswers(el) {
        const questions = [];
        for (const questionEl of el.querySelectorAll(".o_wslides_js_lesson_quiz_question")) {
            const answers = [];
            for (const answerEl of questionEl.querySelectorAll(".o_wslides_quiz_answer")) {
                const answerData = getDataFromEl(answerEl);
                answers.push({
                    id: answerData.answerId,
                    text: answerData.text,
                });
            }
            const questionData = getDataFromEl(questionEl);
            questions.push({
                id: questionData.questionId,
                title: questionData.title,
                answer_ids: answers,
            });
        }
        return questions;
    },
    getData() {
        const el = document.querySelector(".o_wslides_js_lesson_quiz"); // TODO: adapt for fullscreen
        if (!el) {
            return { hasQuiz: false };
        }
        // TODO: explicitly get all fields OR not
        // TODO: move methods which modify data to service
        const questions = this.extractQuestionsAndAnswers(el);
        const data = Object.assign(
            {
                hasQuiz: true,
                id: 0,
                name: "",
                hasNext: false,
                completed: false,
                isMember: false,
                isMemberOrInvited: false,
                questions,
                questionCount: questions.length,
                sessionAnswers: [],
                answers: [],
                quizKarmaWon: 0,
                channelRequestedAccess: false,
                publicUser: session.is_website_user,
                userId: user.userId,
                redirectURL: encodeURIComponent(document.URL),
                currentlyEditedQuestions: {},
            },
            getDataFromEl(el)
        );
        return data;
    },
    start() {
        const data = this.getData();
        return {
            get: () => data,
            beginUpdatingQuestion: (question) => {
                data.currentlyEditedQuestions[question.id] = question;
            },
            endUpdatingQuestion: (question) => {
                delete data.currentlyEditedQuestions[question.id];
            },
            /*
             * Fetch the quiz for a particular slide
             */
            // TODO: remove this once certain that not needed in toggle...
            async fetchQuiz() {
                const quizData = await rpc("/slides/slide/quiz/get", {
                    slide_id: data.id,
                });
                Object.assign(data, {
                    sessionAnswers: quizData.session_answers,
                    descriptionSafe: quizData.slide_description
                        ? markup(quizData.slide_description)
                        : "",
                    questions: quizData.slide_questions || [],
                    questionsCount: quizData.slide_questions.length,
                    quizAttemptsCount: quizData.quiz_attempts_count || 0,
                    quizKarmaGain: quizData.quiz_karma_gain || 0,
                    quizKarmaWon: quizData.quiz_karma_won || 0,
                    slideResources: quizData.slide_resource_ids || [],
                });
            },
        };
    },
};

const courseJoinService = {
    dependencies: [],
    start() {
        let beforeJoin = async () => {};
        let afterJoin = async () => document.location.reload();
        return {
            registerBeforeJoin: (f) => {
                beforeJoin = f;
            },
            registerAfterJoin: (f) => {
                afterJoin = f;
            },
            joinChannel: async (channelId) => {
                const data = await rpc("/slides/channel/join", { channel_id: channelId });
                if (!data.error) {
                    await afterJoin();
                }
                return data;
            },
            beforeJoin: () => beforeJoin(),
            afterJoin: () => afterJoin(),
        };
    },
};

registry.category("services").add("slides_course_quiz", quizService);
registry.category("services").add("slides_course_join", courseJoinService);
