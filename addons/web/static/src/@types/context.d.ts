declare module "@web/core/context" {
    export interface Context {
        lang?: string;
        tz?: string;
        uid?: number | false;
        allowed_company_ids?: number[];
        [key: string]: any;
    }

    export type ContextDescription = Context | string | undefined;

    export function makeContext(
        contexts: ContextDescription[],
        initialEvaluationContext?: Context
    ): Context;

    export function evalPartialContext(
        context: string,
        evaluationContext?: Context
    ): Context;
}
