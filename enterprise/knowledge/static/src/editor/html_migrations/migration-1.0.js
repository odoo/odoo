import { decodeDataBehaviorProps, getPropNameNode } from "@knowledge/editor/html_migrations/utils";
import { getOrigin } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

export function upgrade(container, env) {
    for (const [key, selector] of Object.entries(selectors)) {
        const elements = container.querySelectorAll(selector);
        if (elements.length) {
            upgrades[key](elements, env);
        }
    }
}

function upgradeSearchModelState(searchModelState) {
    searchModelState = JSON.parse(searchModelState);
    const dfOptMap = {
        this_year: "year",
        last_year: "year-1",
        antepenultimate_year: "year-2",
        this_month: "month",
        last_month: "month-1",
        antepenultimate_month: "month-2",
    };
    for (const searchItem of Object.values(searchModelState.searchItems)) {
        if (searchItem.type === "dateFilter") {
            const newDefaults = new Set();
            for (const generatorId of searchItem.defaultGeneratorIds) {
                if (generatorId in dfOptMap) {
                    newDefaults.add(dfOptMap[generatorId]);
                }
            }
            if (newDefaults.size) {
                searchItem.defaultGeneratorIds = Array.from(newDefaults);
            }
            if (!searchItem.optionsParams) {
                searchItem.optionsParams = {
                    startYear: -2,
                    endYear: 0,
                    startMonth: -2,
                    endMonth: 0,
                    customOptions: [],
                };
            }
            for (const queryItem of searchModelState.query) {
                if (
                    queryItem.searchItemId === searchItem.id &&
                    queryItem.generatorId &&
                    queryItem.generatorId in dfOptMap
                ) {
                    queryItem.generatorId = dfOptMap[queryItem.generatorId];
                }
            }
        }
    }
    return JSON.stringify(searchModelState);
}

const selectors = {
    articleBehavior: ".o_knowledge_behavior_type_article",
    articlesStructureBehavior: ".o_knowledge_behavior_type_articles_structure",
    comments: ".knowledge-thread-comment",
    drawBehavior: ".o_knowledge_behavior_type_draw",
    embeddedViewBehavior: ".o_knowledge_behavior_type_embedded_view",
    fileBehavior: ".o_knowledge_behavior_type_file",
    tableOfContentBehavior: ".o_knowledge_behavior_type_toc",
    templateBehavior: ".o_knowledge_behavior_type_template",
    videoBehavior: ".o_knowledge_behavior_type_video",
    viewLinkBehavior: ".o_knowledge_behavior_type_view_link",
};

const upgrades = {
    articleBehavior: (elements) => {
        for (const el of elements) {
            const oldProps = decodeDataBehaviorProps(el.dataset.behaviorProps);
            if (!oldProps?.article_id || !oldProps?.display_name) {
                // Abort the conversion if data can not be recovered.
                // Element will still exist in the DOM as raw data.
                continue;
            }
            delete el.dataset.behaviorProps;
            el.dataset.res_id = oldProps?.article_id;
            el.removeAttribute("tabindex");
            el.classList.remove("o_knowledge_behavior_anchor", "o_knowledge_behavior_type_article");
            el.classList.add("o_knowledge_article_link");
            el.replaceChildren(document.createTextNode(oldProps.display_name));
        }
    },
    articlesStructureBehavior: (elements) => {
        function buildIndex(el, props) {
            const index = [];
            while (el) {
                const anchor = el.querySelector("a");
                const id = parseInt(
                    anchor
                        .getAttribute("href")
                        .match(/(\d+)$/)
                        .at(1)
                );
                const name = anchor.textContent;
                const article = { id, name, childIds: [] };
                el = el.nextElementSibling;
                const child = el?.querySelector(":scope > ol > li");
                if (child) {
                    article.childIds = buildIndex(child, props);
                    props.showAllChildren = true;
                    el = el.nextElementSibling;
                }
                index.push(article);
            }
            return index;
        }
        for (const el of elements) {
            const props = {};
            try {
                const content = getPropNameNode("content", el);
                const articles = buildIndex(content.querySelector("li"), props);
                if (articles.length) {
                    props.articles = articles;
                    el.dataset.embeddedProps = JSON.stringify(props);
                }
            } catch {
                // ignore the existing article index if the parsing fails, it will
                // have to be refreshed manually.
            }
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.dataset.embedded = "articleIndex";
            el.replaceChildren();
        }
    },
    comments: (elements, env) => {
        function createBeacon({ type, threadId, resId, resModel, disabled }) {
            const anchor = document.createElement("A");
            anchor.classList.add("oe_unremovable", "oe_thread_beacon");
            anchor.dataset.id = threadId;
            anchor.dataset.res_id = resId;
            anchor.dataset.resModel = resModel;
            anchor.dataset.oeType = type;
            if (disabled) {
                anchor.classList.add("oe_disabled_thread_beacon");
            }
            return anchor;
        }
        function createBeacons({ anchors, threadId, resId, resModel }) {
            const start = anchors.at(0);
            const end = anchors.at(-1);
            if (!start || !end) {
                return;
            }
            const disabled = !start.classList.contains("knowledge-thread-highlighted-comment");
            const beaconStart = createBeacon({
                type: "threadBeaconStart",
                threadId,
                resId,
                resModel,
                disabled,
            });
            const beaconEnd = createBeacon({
                type: "threadBeaconEnd",
                threadId,
                resId,
                resModel,
                disabled,
            });
            start.before(beaconStart);
            end.after(beaconEnd);
        }
        function groupComments(anchors) {
            const comments = {};
            for (const anchor of anchors) {
                const threadId = anchor.dataset.id;
                if (!threadId) {
                    continue;
                }
                comments[threadId] ||= [];
                comments[threadId].push(anchor);
            }
            return comments;
        }
        const resId = env.model?.root?.resId;
        const resModel = env.model?.root?.resModel;
        if (resId && resModel) {
            // Only create new comment beacons if the env has a record.
            const comments = groupComments(elements);
            for (const threadId in comments) {
                createBeacons({ anchors: comments[threadId], threadId, resId, resModel });
            }
        }
        // Remove old comments anchors (not a big deal if there is no replacement for some)
        for (const el of [...elements]) {
            if (el.nodeName === "SPAN") {
                const childNodes = [];
                while (el.firstChild) {
                    childNodes.push(el.firstChild);
                    el.firstChild.remove();
                }
                el.replaceWith(...childNodes);
                continue;
            }
            el.classList.remove(
                "focused-comment",
                "knowledge-thread-highlighted-comment",
                "knowledge-thread-comment"
            );
            delete el.dataset.id;
            el.removeAttribute("tabindex");
        }
    },
    drawBehavior: (elements) => {
        for (const el of elements) {
            const oldProps = decodeDataBehaviorProps(el.dataset.behaviorProps);
            if (!oldProps || !oldProps.source) {
                // Abort the conversion if data can not be recovered.
                // Element will still exist in the DOM as raw data.
                continue;
            }
            const props = {
                height: oldProps.height,
                source: oldProps.source,
                width: oldProps.width,
            };
            el.dataset.embedded = "draw";
            el.dataset.embeddedProps = JSON.stringify(props);
            delete el.dataset.behaviorProps;
            delete el.dataset.oeTransientContent;
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.replaceChildren();
        }
    },
    embeddedViewBehavior: (elements) => {
        for (const el of elements) {
            const oldProps = decodeDataBehaviorProps(el.dataset.behaviorProps);
            const viewProps = {
                context: oldProps.context,
                displayName: oldProps.display_name,
                favoriteFilters: {},
                id: oldProps.embedded_view_id,
                viewType: oldProps.view_type,
            };
            if (oldProps.act_window) {
                viewProps.actWindow = oldProps.act_window;
            } else {
                viewProps.actionXmlId = oldProps.action_xml_id;
            }
            if (oldProps.additionalViewProps) {
                viewProps.additionalViewProps = oldProps.additionalViewProps;
            }
            if (oldProps.favorites) {
                // favorites was an array, is now an object
                for (const filter of oldProps.favorites) {
                    viewProps.favoriteFilters[filter.name] = filter;
                }
            }
            if (viewProps.context.knowledge_search_model_state) {
                viewProps.context.knowledge_search_model_state = upgradeSearchModelState(
                    viewProps.context.knowledge_search_model_state
                );
            }
            delete el.dataset.behaviorProps;
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.dataset.embedded = "view";
            el.dataset.embeddedProps = JSON.stringify({ viewProps });
            el.replaceChildren();
        }
    },
    fileBehavior: (elements) => {
        for (const el of elements) {
            const oldProps = decodeDataBehaviorProps(el.dataset.behaviorProps);
            const htmlFileName = getPropNameNode("fileName", el)?.textContent;
            const htmlFileExtension = getPropNameNode("fileExtension", el)?.textContent;
            const htmlFileImageLink = getPropNameNode("fileImage", el)?.querySelector("a");
            const href = htmlFileImageLink?.getAttribute("href");
            const mimetype = htmlFileImageLink?.dataset.mimetype;
            let accessToken, checksum, id, type, url;
            if (href?.startsWith(getOrigin())) {
                id = parseInt((href.match(/\/web\/(?:content|image)\/(\d+)/) || [])[1]);
                checksum = (href.match(/unique=([^&]+)/) || [])[1];
                accessToken = (href.match(/access_token=([^&]+)/) || [])[1];
            }
            if (!id) {
                type = "url";
                url = href?.replace(/\?.*$/, "");
            } else {
                type = "binary";
            }
            const fileName = htmlFileName || oldProps?.fileName || _t("Untitled");
            const extension = htmlFileExtension || oldProps?.fileExtension;
            let fileData = oldProps?.fileData;
            // accessToken has been renamed in file_model
            if (fileData?.accessToken) {
                fileData.access_token = fileData.accessToken;
                delete fileData.accessToken;
            }
            if (!id && !url && !fileData) {
                // Abort the conversion if data can not be recovered.
                // Element will still exist in the DOM as raw data.
                continue;
            }
            if (!fileData) {
                fileData = {
                    access_token: accessToken,
                    checksum,
                    extension,
                    filename: fileName,
                    id,
                    mimetype,
                    name: fileName,
                    type,
                    url,
                };
            }
            const props = {
                fileData,
            };
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            delete el.dataset.behaviorProps;
            el.dataset.embedded = "file";
            el.dataset.embeddedProps = JSON.stringify(props);
            el.replaceChildren();
        }
    },
    tableOfContentBehavior: (elements) => {
        for (const el of elements) {
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.dataset.embedded = "tableOfContent";
            el.replaceChildren();
        }
    },
    templateBehavior: (elements) => {
        for (const el of elements) {
            let content = getPropNameNode("content", el);
            if (!content) {
                content = document.createElement("DIV");
                const p = document.createElement("P");
                const br = document.createElement("BR");
                p.append(br);
                content.append(p);
            }
            content.removeAttribute("class");
            delete content.dataset.propName;
            content.dataset.embeddedEditable = "clipboardContent";
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.dataset.embedded = "clipboard";
            el.replaceChildren(content);
        }
    },
    videoBehavior: (elements) => {
        for (const el of elements) {
            const oldProps = decodeDataBehaviorProps(el.dataset.behaviorProps);
            if (!oldProps || !oldProps.platform || !oldProps.videoId) {
                // Abort the conversion if data can not be recovered.
                // Element will still exist in the DOM as raw data.
                continue;
            }
            delete el.dataset.behaviorProps;
            const props = {
                platform: oldProps.platform,
                videoId: oldProps.videoId,
                params: oldProps.params,
            };
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.dataset.embedded = "video";
            el.dataset.embeddedProps = JSON.stringify(props);
            el.replaceChildren();
        }
    },
    viewLinkBehavior: (elements) => {
        for (const el of elements) {
            const oldProps = decodeDataBehaviorProps(el.dataset.behaviorProps);
            const viewProps = {
                context: oldProps.context,
                displayName: oldProps.name,
                viewType: oldProps.view_type,
            };
            const props = {};
            if (oldProps.style) {
                props.linkStyle = oldProps.style;
            }
            if (oldProps.act_window) {
                viewProps.actWindow = oldProps.act_window;
            } else {
                viewProps.actionXmlId = oldProps.action_xml_id;
            }
            if (viewProps.context.knowledge_search_model_state) {
                viewProps.context.knowledge_search_model_state = upgradeSearchModelState(
                    viewProps.context.knowledge_search_model_state
                );
            }
            delete el.dataset.behaviorProps;
            el.removeAttribute("class");
            el.removeAttribute("tabindex");
            el.dataset.embedded = "viewLink";
            el.dataset.embeddedProps = JSON.stringify({ viewProps, ...props });
            el.replaceChildren();
        }
    },
};
