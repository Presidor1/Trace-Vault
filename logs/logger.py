# tracevault/logs/logger.py

import logging
import os
from logging.handlers import RotatingFileHandler

# --- Configuration ---

# 1. Define the log format for consistency
LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "[%(filename)s:%(lineno)d] | %(message)s"
)

# 2. Set the default logging level
# Use INFO as default, but allow overriding via environment variable
DEFAULT_LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a highly-configured logger instance.

    Args:
        name: The name of the logger (usually __name__ of the calling module).
    """
    logger = logging.getLogger(name)
    
    # Prevents duplicate log entries if the logger is configured elsewhere
    if logger.handlers:
        return logger 
    
    # Set the logging level
    try:
        logger.setLevel(DEFAULT_LOG_LEVEL)
    except ValueError:
        logger.setLevel(logging.INFO)
        logger.warning(f"Invalid LOG_LEVEL '{DEFAULT_LOG_LEVEL}'. Defaulting to INFO.")

    # --- Handler 1: Console Handler (for Render/Stdout) ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # --- Handler 2: Optional File Handler (for Local Debugging) ---
    # Only enable this if a LOG_FILE environment variable is set.
    log_file_path = os.environ.get('LOG_FILE')
    if log_file_path:
        # Use a RotatingFileHandler to prevent the log file from growing indefinitely
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024, # 10 MB limit
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)

    # Note: If running a multi-process/worker system (like with our future queue),
    # it's critical that each process logs to standard output (stdout/stderr)
    # or uses a centralized system (like a database or log collector), 
    # as file-based logging is generally unsafe across processes.
    # Our setup prioritizes the robust Console Handler.

    return logger

# Example of how to use this from any module:
# from tracevault.logs.logger import get_logger
# logger = get_logger(__name__)
# logger.info("Application started.")
