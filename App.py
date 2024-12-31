from Helpers.ServiceApp import app

from waitress import serve
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

if __name__=='__main__':
    # serve(app, host='0.0.0.0', port=5000)
    app.run(debug=True)
