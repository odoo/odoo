// TODO: store all quiz related data
// TODO: move to other folder
import { registry } from "@web/core/registry";
import { getDataFromEl } from "@web/public/utils";
import { user } from "@web/core/user";
import { session } from "@web/session";

// TODO: check naming convention for services
const quizService = {
    dependencies: [],
    extractChannelData(slideData) {
        return {
            channelId: slideData.channelId,
            channelEnroll: slideData.channelEnroll,
            channelRequestedAccess: slideData.channelRequestedAccess || false,
            signupAllowed: slideData.signupAllowed,
        };
    },

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
        console.log("QuizData:", data);
        return data;
    },
    start() {
        const data = this.getData();
        return {
            get: () => data,
            updateQuestion: (question) => {
                data.currentlyEditedQuestions[question.id] = question;
            },
        };
    },
};

const courseJoinService = {
    dependencies: [],
    start() {
        let beforeJoinFunction = () => Promise.resolve();
        let afterJoinFunction = () => document.location.reload();
        return {
            registerBeforeJoin: (f) => {
                beforeJoinFunction = f;
            },
            registerAfterJoin: (f) => {
                afterJoinFunction = f;
            },
            beforeJoin: () => beforeJoinFunction(),
            afterJoin: () => afterJoinFunction(),
        };
    },
};

registry.category("services").add("slides_course_quiz", quizService);
registry.category("services").add("slides_course_join", courseJoinService);
