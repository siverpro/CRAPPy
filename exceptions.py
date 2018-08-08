from requests.exceptions import HTTPError

class HTTP500(HTTPError):
    """
   The Web server (running the Web Site) encountered an unexpected condition
   that prevented it from fulfilling the request by the client (e.g. your Web
   browser or our CheckUpDown robot) for access to the requested URL.
   """
 
    def __str__(self):
        return repr('500 Internal server error')
 
 
class HTTP400(HTTPError):
    """
   Http400 Error Exception
   The server cannot or will not process the request due to
   an apparent client error e.g., malformed request syntax,
   invalid request message framing, or deceptive request routing).
   """
 
    def __str__(self):
        return repr('400  Bad Request')
 
 
class HTTP401(HTTPError):
    """
   Http401 Error Exception
   Similar to 403 Forbidden, but specifically for use when authentication
   is required and has failed or has not yet been provided.
   The response must include a WWW-Authenticate header field containing
   a challenge applicable to the requested resource.
   """
 
    def __str__(self):
        return repr('401 Unauthorized')
 
 
class HTTP403(HTTPError):
    """
   Http403 Error Exception
   The request was a valid request, but the server is refusing to respond to it.
   403 error semantically means "unauthorized", i.e. the user does not
   have the necessary permissions for the resource.
   """
 
    def __str__(self):
        return repr('403 Forbidden')
 
 
class HTTP404(HTTPError):
    """
   Http404 Error Exception
   The requested resource could not be found but may be available in the future.
   Subsequent response by the client are permissible.
   """
    def __str__(self):
        return repr('404 not Found occurred')
 
 
class HTTP405(HTTPError):
    """
   Http405 Error Exception
   A request method is not supported for the requested resource; for example,
   a GET request on a form which requires data to be presented via POST, or a
   PUT request on a read-only resource.
   """
    def __str__(self):
        return repr('405 Method Not Allowed')
 
class HTTP415(HTTPError):
 
    def __str__(self):
        return repr('415 Wrong media type. application/json only.')
 
class HTTP429(HTTPError):
    """
   Http429 Error Exception
   The user has sent too many response in a given amount of time.
   Intended for use with rate limiting schemes.
   """
    def __str__(self):
        return repr('429 Too Many Requests')
 
 
class HTTP503(HTTPError):
    """
   Http503 Error Exception
   The server is currently unavailable (because it is overloaded or
   down for maintenance). Generally, this is a temporary state.
   """
    def __str__(self):
        return repr('503 Service Unavailable')