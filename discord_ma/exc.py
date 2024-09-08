class InvalidEventError(Exception):
    def __init__(self, message="The provided event name invalid."):
        super().__init__(message)