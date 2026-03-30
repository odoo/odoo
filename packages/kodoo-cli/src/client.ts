export interface ModuleRecord {
    id: number;
    app_id: number;
    name: string;
    technical_name: string;
    state: string;
    version?: string;
    depends?: string;
    app_name?: string;
    app_technical_name?: string;
}

export interface ValidationError {
    rule: string;
    entity: string;
    message: string;
}

export interface ValidateResponse {
    valid: boolean;
    errors: ValidationError[];
}

export interface BuildFile {
    path: string;
    content_hash: string;
    model_hash: string;
    size_bytes?: number;
}

export interface BuildResponse {
    build_id: number;
    files: BuildFile[];
}

export interface DiffResult {
    changed: string[];
    added: string[];
    removed: string[];
    clean: boolean;
}

export type PublishMode = "runtime" | "export" | "both";

export interface PublishResponse {
    published: boolean;
    applied: string[];
    errors: string[];
}

export interface SnapshotResponse {
    snapshot_id: number;
    module_id: number;
    name: string;
}

export interface SnapshotRecord {
    id: number;
    name: string;
    created_at?: string | null;
    created_by?: string | null;
}

export interface RollbackResponse {
    rolled_back: boolean;
    module_id: number;
    snapshot_id: number;
    pre_snapshot_id: number;
}

export interface ConflictRecord {
    artifact_id: number;
    file_path: string;
    block_id: string;
    generated_content: string | null;
    current_content: string | null;
}

export interface ConflictsResponse {
    conflicts: ConflictRecord[];
    warnings: string[];
    output_path?: string;
}

type RequestQuery = Record<string, string | undefined>;

export class ForgeClientError extends Error {
    status: number;
    detail: unknown;

    constructor(message: string, status: number, detail: unknown) {
        super(message);
        this.name = "ForgeClientError";
        this.status = status;
        this.detail = detail;
    }
}

function extractErrorMessage(detail: unknown, fallback: string): string {
    if (typeof detail === "string" && detail.trim()) {
        return detail;
    }
    if (detail && typeof detail === "object") {
        const record = detail as Record<string, unknown>;
        if (typeof record.detail === "string" && record.detail.trim()) {
            return record.detail;
        }
        if (Array.isArray(record.errors)) {
            return "Validation failed";
        }
        if (Array.isArray(record.conflicts)) {
            return "Build conflicts detected";
        }
    }
    return fallback;
}

export class ForgeClient {
    private readonly engineUrl: string;

    constructor(engineUrl: string) {
        this.engineUrl = engineUrl.replace(/\/+$/, "");
    }

    private buildUrl(pathname: string, query?: RequestQuery): string {
        const url = new URL(`${this.engineUrl}${pathname}`);
        if (query) {
            for (const [key, value] of Object.entries(query)) {
                if (value) {
                    url.searchParams.set(key, value);
                }
            }
        }
        return url.toString();
    }

    private async request<T>(
        method: string,
        pathname: string,
        options?: { body?: unknown; query?: RequestQuery },
    ): Promise<T> {
        const headers = new Headers();
        let body: string | undefined;
        if (options?.body !== undefined) {
            headers.set("Content-Type", "application/json");
            body = JSON.stringify(options.body);
        }
        const response = await fetch(this.buildUrl(pathname, options?.query), {
            method,
            headers,
            body,
        });
        const text = await response.text();
        let payload: unknown = null;
        if (text) {
            try {
                payload = JSON.parse(text) as unknown;
            } catch {
                payload = text;
            }
        }
        if (!response.ok) {
            const detail =
                payload && typeof payload === "object" && "detail" in (payload as Record<string, unknown>)
                    ? (payload as Record<string, unknown>).detail
                    : payload;
            throw new ForgeClientError(
                extractErrorMessage(detail, `${method} ${pathname} failed with ${response.status}`),
                response.status,
                detail,
            );
        }
        return payload as T;
    }

    async listModules(filters?: {
        technicalName?: string;
        app?: string;
    }): Promise<ModuleRecord[]> {
        return this.request<ModuleRecord[]>("GET", "/modules", {
            query: {
                technical_name: filters?.technicalName,
                app: filters?.app,
            },
        });
    }

    async getModule(id: number): Promise<ModuleRecord> {
        return this.request<ModuleRecord>("GET", `/modules/${id}`);
    }

    async resolveModule(name: string): Promise<ModuleRecord> {
        const modules = await this.listModules({ technicalName: name });
        if (modules.length === 0) {
            throw new Error(
                `Module '${name}' not found. Use 'kodoo forge list' to see available modules.`,
            );
        }
        if (modules.length > 1) {
            const apps = modules
                .map((module) => module.app_technical_name || String(module.app_id))
                .join(", ");
            throw new Error(`Module '${name}' is ambiguous across apps: ${apps}.`);
        }
        return modules[0];
    }

    async validate(id: number): Promise<ValidateResponse> {
        return this.request<ValidateResponse>("POST", `/pipeline/${id}/validate`);
    }

    async build(id: number): Promise<BuildResponse> {
        return this.request<BuildResponse>("POST", `/pipeline/${id}/build`);
    }

    async *buildStream(id: number): AsyncIterator<BuildResponse> {
        yield await this.build(id);
    }

    async diff(id: number): Promise<DiffResult> {
        return this.request<DiffResult>("GET", `/pipeline/${id}/diff`);
    }

    async publish(id: number, mode: PublishMode): Promise<PublishResponse> {
        return this.request<PublishResponse>("POST", `/pipeline/${id}/publish`, {
            body: { mode },
        });
    }

    async snapshot(id: number, name: string): Promise<SnapshotResponse> {
        return this.request<SnapshotResponse>("POST", `/pipeline/${id}/snapshot`, {
            body: { name },
        });
    }

    async listSnapshots(id: number): Promise<SnapshotRecord[]> {
        return this.request<SnapshotRecord[]>("GET", `/pipeline/${id}/snapshots`);
    }

    async rollback(id: number, snapshotId: number): Promise<RollbackResponse> {
        return this.request<RollbackResponse>("POST", `/pipeline/${id}/rollback/${snapshotId}`);
    }

    async conflicts(id: number): Promise<ConflictsResponse> {
        return this.request<ConflictsResponse>("GET", `/pipeline/${id}/conflicts`);
    }
}
