PRAGMA enable_verification;

CREATE TABLE IF NOT EXISTS labelers (
    labeler_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS trace_runs (
    run_id TEXT PRIMARY KEY,
    prompt_path TEXT,
    prompt_checksum TEXT,
    source_csv TEXT,
    model_name TEXT,
    generated_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS emails_raw (
    email_hash TEXT PRIMARY KEY,
    subject TEXT,
    body TEXT,
    metadata JSON,
    run_id TEXT,
    ingested_at TIMESTAMP DEFAULT current_timestamp,
    FOREIGN KEY (run_id) REFERENCES trace_runs(run_id)
);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    email_hash TEXT,
    labeler_id TEXT,
    open_code TEXT,
    pass_fail BOOLEAN,
    run_id TEXT,
    created_at TIMESTAMP DEFAULT current_timestamp,
    updated_at TIMESTAMP,
    FOREIGN KEY (email_hash) REFERENCES emails_raw(email_hash),
    FOREIGN KEY (labeler_id) REFERENCES labelers(labeler_id),
    FOREIGN KEY (run_id) REFERENCES trace_runs(run_id)
);

CREATE TABLE IF NOT EXISTS failure_modes (
    failure_mode_id TEXT PRIMARY KEY,
    slug TEXT,
    display_name TEXT,
    definition TEXT,
    examples JSON,
    created_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS axial_links (
    annotation_id TEXT,
    failure_mode_id TEXT,
    run_id TEXT,
    linked_at TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (annotation_id, failure_mode_id),
    FOREIGN KEY (annotation_id) REFERENCES annotations(annotation_id),
    FOREIGN KEY (failure_mode_id) REFERENCES failure_modes(failure_mode_id),
    FOREIGN KEY (run_id) REFERENCES trace_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_annotations_email_hash ON annotations(email_hash);
CREATE INDEX IF NOT EXISTS idx_annotations_run_id ON annotations(run_id);
CREATE INDEX IF NOT EXISTS idx_emails_run_id ON emails_raw(run_id);
CREATE INDEX IF NOT EXISTS idx_axial_links_run_id ON axial_links(run_id);
