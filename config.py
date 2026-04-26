from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "2020_05_26"
REF_DIR = BASE_DIR / "data_release_v3.5"

TRACE_FILES = {
    "osb":            DATA_DIR / "call_chain_metrics/trace_osb.csv",
    "csf":            DATA_DIR / "call_chain_metrics/trace_csf.csv",
    "remote_process": DATA_DIR / "call_chain_metrics/trace_remote_process.csv",
    "fly_remote":     DATA_DIR / "call_chain_metrics/trace_fly_remote.csv",
    "local":          DATA_DIR / "call_chain_metrics/trace_local.csv",
    "jdbc":           DATA_DIR / "call_chain_metrics/trace_jdbc.csv",
}

PLATFORM_FILES = {
    "os":        DATA_DIR / "platform_metrics/os_linux.csv",
    "db":        DATA_DIR / "platform_metrics/db_oracle_11g.csv",
    "redis":     DATA_DIR / "platform_metrics/mw_redis.csv",
    "docker":    DATA_DIR / "platform_metrics/dcos_docker.csv",
    "container": DATA_DIR / "platform_metrics/dcos_container.csv",
}

ESB_FILE     = DATA_DIR / "business_metrics/esb.csv"
FAULT_FILE   = REF_DIR  / "0_fault_description.xlsx"
ARCH_FILE    = REF_DIR  / "1_application_deployment_architecture_list.xlsx"

# Fault log timestamps are stored as CST (UTC+8)
CST_OFFSET_HOURS = 8

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_TOOL_ROUNDS = 15
