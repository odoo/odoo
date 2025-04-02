import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { markup, EventBus } from "@odoo/owl";

const websiteSlidesService = {
    dependencies: [],
    filter(object) {
        for (const key of Object.keys(object)) {
            if (object[key] == undefined) {
                delete object[key];
            }
        }
        return object;
    },
    start() {
        let setSlideReady;
        let setQuizReady;
        const quizCache = {};
        const ready = {
            slide: new Promise((resolve) => (setSlideReady = resolve)),
            quiz: new Promise((resolve) => (setQuizReady = resolve)),
        };
        const data = {
            slides: [],
            // current slide
            slide: {
                id: undefined,
                name: undefined,
                category: undefined,
                hasQuestion: false,
                canSelfMarkCompleted: undefined,
                canSelfMarkUncompleted: undefined,
                completed: undefined,
                hasNext: undefined,
                nextSlideUrl: undefined,
                uncompletedIcon: undefined,
                // fullscreen only fields
                htmlContent: undefined,
                embedUrl: undefined,
                embedCode: undefined,
                isQuiz: false,
                autoSetDone: undefined,
                videoSourceType: undefined,
                canAccess: undefined,
                slug: undefined,
                websiteShareUrl: undefined,
                emailSharing: undefined,
            },
            quiz: {
                answers: [],
                sessionAnswers: [],
                questions: [],
                questionCount: undefined,
                attemptsCount: undefined,
                karmaGain: undefined,
                karmaWon: undefined,
                karmaMax: undefined,
                descriptionSafe: undefined,
                slideResources: [],
                rankProgress: undefined,
            },
            channel: {
                id: undefined,
                enroll: undefined,
                canUpload: undefined,
                inviteHash: undefined,
                invitePartnerId: undefined,
                invitePreview: undefined,
                isMember: undefined,
                isMemberOrInvited: undefined,
                completion: undefined,
                requestedAccess: undefined,
            },
            user: {
                id: user.userId,
                public: session.is_website_user,
                signupAllowed: undefined,
                isPartnerWithoutUser: undefined,
            },
        };
        let beforeJoin = async () => {};
        let afterJoin = async () => document.location.reload();
        return {
            data,
            ready,
            bus: new EventBus(),
            setSlides: (slides) => {
                data.slides.length = 0;
                data.slides.push(...slides);
            },
            setChannel: (channel) => {
                Object.assign(data.channel, this.filter(channel));
            },
            setSlide: (slide, removeOld = false) => {
                // update corresponding slide stored in data.slides
                if (slide.id !== data.slide.id || slide.isQuiz !== data.slide.isQuiz) {
                    const index = data.slides.findIndex(
                        (slide) => slide.id === data.slide.id && slide.isQuiz === data.slide.isQuiz
                    );
                    if (index != -1) {
                        Object.assign(data.slides[index], data.slide);
                    }
                }
                if (removeOld) {
                    for (const key of Object.keys(data.slide)) {
                        delete data.slide[key];
                    }
                }
                Object.assign(data.slide, this.filter(slide));
                setSlideReady();
            },
            setQuiz: (quiz, removeOld = false) => {
                if (removeOld) {
                    for (const key of Object.keys(data.quiz)) {
                        delete data.quiz[key];
                    }
                }
                Object.assign(data.quiz, this.filter(quiz));
                quizCache[data.slide.id] = structuredClone(data.quiz);
                setQuizReady();
            },
            setUser: (user) => {
                Object.assign(data.user, this.filter(user));
            },
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
            async fetchQuiz(force = false) {
                const quiz = quizCache[data.slide.id];
                if (quiz && !force) {
                    Object.assign(data.quiz, quiz);
                } else {
                    const quizData = await rpc("/slides/slide/quiz/get", {
                        slide_id: data.slide.id,
                    });
                    Object.assign(data.quiz, {
                        sessionAnswers: quizData.session_answers || [],
                        descriptionSafe: quizData.slide_description
                            ? markup(quizData.slide_description)
                            : "",
                        questions: quizData.slide_questions || [],
                        questionCount: quizData.slide_questions.length,
                        attemptsCount: quizData.quiz_attempts_count || 0,
                        karmaGain: quizData.quiz_karma_gain || 0,
                        karmaWon: quizData.quiz_karma_won || 0,
                        karmaMax: quizData.quiz_karma_max || 0,
                        slideResources: quizData.slide_resource_ids || [],
                    });
                }
                quizCache[data.slide.id] = structuredClone(data.quiz);
                data.slide.hasQuestion = data.quiz.questionCount > 0;
                setQuizReady();
            },
        };
    },
};

registry.category("services").add("website_slides", websiteSlidesService);
