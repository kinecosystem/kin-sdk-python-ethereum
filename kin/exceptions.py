

# All exceptions should subclass from SdkError in this module.
class SdkError(Exception):
    """Base class for all SDK errors."""


class SdkConfigurationError(SdkError):
    pass


class SdkNotConfiguredError(SdkError):
    pass

