-- CHAR9000 append-only audit log. Rows may be inserted, never updated or deleted.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS char9000_audit;

CREATE TABLE IF NOT EXISTS char9000_audit.audit_log (
    id              BIGSERIAL PRIMARY KEY,
    logged_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    node            TEXT        NOT NULL,
    actor           TEXT        NOT NULL,      -- e.g. 'char9000', 'crewai:planner'
    requested_by    TEXT,                      -- human email, or NULL if self-initiated
    approved_by     TEXT,                      -- approver email when the action was gated
    autonomy_level  SMALLINT    NOT NULL,
    action          TEXT        NOT NULL,
    target          TEXT,
    result          TEXT        NOT NULL,      -- 'success' | 'failure' | 'proposed' | ...
    details         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    prev_hash       TEXT,
    row_hash        TEXT
);

-- Hash chain: each row's hash covers its content plus the previous row's hash.
CREATE OR REPLACE FUNCTION char9000_audit.chain_hash() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(9000);
    SELECT row_hash INTO NEW.prev_hash FROM char9000_audit.audit_log ORDER BY id DESC LIMIT 1;
    NEW.logged_at := now();
    NEW.row_hash := encode(digest(
        coalesce(NEW.prev_hash,'') || '|' || NEW.logged_at::text || '|' || NEW.node || '|' || NEW.actor || '|' ||
        coalesce(NEW.requested_by,'') || '|' || coalesce(NEW.approved_by,'') || '|' || NEW.autonomy_level::text || '|' ||
        NEW.action || '|' || coalesce(NEW.target,'') || '|' || NEW.result || '|' || NEW.details::text,
        'sha256'), 'hex');
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION char9000_audit.deny_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'char9000_audit.audit_log is append-only: % is not permitted', TG_OP;
END $$;

DROP TRIGGER IF EXISTS audit_chain       ON char9000_audit.audit_log;
DROP TRIGGER IF EXISTS audit_no_update   ON char9000_audit.audit_log;
DROP TRIGGER IF EXISTS audit_no_delete   ON char9000_audit.audit_log;
DROP TRIGGER IF EXISTS audit_no_truncate ON char9000_audit.audit_log;
CREATE TRIGGER audit_chain       BEFORE INSERT   ON char9000_audit.audit_log FOR EACH ROW EXECUTE FUNCTION char9000_audit.chain_hash();
CREATE TRIGGER audit_no_update   BEFORE UPDATE   ON char9000_audit.audit_log FOR EACH ROW EXECUTE FUNCTION char9000_audit.deny_change();
CREATE TRIGGER audit_no_delete   BEFORE DELETE   ON char9000_audit.audit_log FOR EACH ROW EXECUTE FUNCTION char9000_audit.deny_change();
CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON char9000_audit.audit_log FOR EACH STATEMENT EXECUTE FUNCTION char9000_audit.deny_change();

-- Writer role: INSERT + SELECT only. Services log through this role, never the superuser.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'char9000_audit_writer') THEN
    CREATE ROLE char9000_audit_writer LOGIN;
  END IF;
END $$;
REVOKE ALL ON char9000_audit.audit_log FROM PUBLIC;
GRANT USAGE ON SCHEMA char9000_audit TO char9000_audit_writer;
GRANT SELECT, INSERT ON char9000_audit.audit_log TO char9000_audit_writer;
GRANT USAGE ON SEQUENCE char9000_audit.audit_log_id_seq TO char9000_audit_writer;

-- Verify the chain: returns rows whose stored hash does not match a recomputation.
CREATE OR REPLACE VIEW char9000_audit.chain_breaks AS
SELECT id, logged_at FROM (
  SELECT a.*, lag(row_hash) OVER (ORDER BY id) AS expected_prev,
         encode(digest(
           coalesce(prev_hash,'') || '|' || logged_at::text || '|' || node || '|' || actor || '|' ||
           coalesce(requested_by,'') || '|' || coalesce(approved_by,'') || '|' || autonomy_level::text || '|' ||
           action || '|' || coalesce(target,'') || '|' || result || '|' || details::text, 'sha256'), 'hex') AS recomputed
  FROM char9000_audit.audit_log a) x
WHERE row_hash <> recomputed OR coalesce(prev_hash,'') <> coalesce(expected_prev,'');
GRANT SELECT ON char9000_audit.chain_breaks TO char9000_audit_writer;
