import os
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
from werkzeug.middleware.proxy_fix import ProxyFix

from iris import app

#if os.environ.get('SCRIPT_NAME') is not None:
#    new_root = os.environ.get('SCRIPT_NAME')
#    app.wsgi_app = DispatcherMiddleware(
#        Response('Not Found', status=404),
#        {
#            new_root: app.wsgi_app
#        }
#    )


if __name__=="__main__":
    app.run()
