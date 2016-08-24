from flask import Flask, jsonify, request, url_for, send_from_directory
from flask_cors import CORS, cross_origin
import requests
from PIL import Image
import imagehash
import os

# TODO from stylize import stylize

STYLES_DIR = './fs/styles'
PHOTOS_DIR = './fs/photos'
ALLOWED_PHOTO_EXTENSIONS = set(['jpg', 'jpeg', 'png'])

app = Flask(__name__, static_url_path='')

# app.config.from_object('keys')
# api_key = app.config['SECRET']

# allowed origins
ORIGINS = ['*']
app.config['CORS_HEADERS'] = "Content-Type"
app.config['CORS_RESOURCES'] = {r"/*": {"origins": ORIGINS}}
cors = CORS(app)

'''
Utility functions
'''
def allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_PHOTO_EXTENSIONS

def photo_filename(photo_hash, style):
    return '{}.{}.jpg'.format(photo_hash, style)

def photo_path(photo_hash, style):
    filename = photo_filename(photo_hash, style)
    return os.path.join(PHOTOS_DIR, filename)

def save_photo(photo_array, path):
    return Image.fromarray(photo_array).save(path)

def get_file(req, filekey='file', allowed_fn=None):
    if filekey not in req.files:
        raise ValueError('you must supply a file')
    file_ = req.files[filekey]
    if not file_:
        raise ValueError('file not provided')
    if allowed_fn and not allowed_fn(file_.filename):
        raise ValueError('file not allowed. do you have a .jpg file extension?')
    return file_



'''
Error handlers
'''
class InvalidUsage(Exception):
    '''straight from flask documentation http://flask.pocoo.org/docs/0.11/patterns/apierrors/'''
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response



'''
API endpoints
'''
@app.route('/api/style/upload', methods=['POST'])
def style_upload():
    try:
        style = get_file(request, allowed_fn=allowed_photo_file)
    except ValueError as err:
        raise InvalidUsage(str(err))

    # check to see if filename conflict in fs
    stylepath = os.path.join(STYLES_DIR, style.filename)
    if os.path.isfile(stylepath):
        raise InvalidUsage('style with same filename already exists')

    # save style to filesystem
    im = Image.open(style)
    im.save(stylepath, 'JPEG')
    return 'upload success'


@app.route('/api/photo/upload', methods=['POST'])
def photo_upload():
    try:
        photo = get_file(request, allowed_fn=allowed_photo_file)
    except ValueError as err:
        raise InvalidUsage(str(err))

    im = Image.open(photo)
    im_hash = str(imagehash.average_hash(im))
    im.save(photo_path(im_hash, 'original'), 'JPEG')
    return jsonify({'uid': im_hash})

@app.route('/api/photo/<photo_hash>/stylize/<filter_name>', methods=['GET'])
def photo_stylize(photo_hash, filter_name):
    # make sure original photo in fs
    if not os.path.isfile(photo_path(photo_hash, 'original')):
        raise InvalidUsage('original photo doesnt exist in the fs')

    # stylize if stylized photo doesn't already exist in fs
    stylized_photo_path = photo_path(photo_hash, filter_name)
    if not os.path.isfile(stylized_photo_path):
        original_photo_path = photo_path(photo_hash, 'original')
        stylized_photo = stylize(original_photo_path, filter_name)
        im = Image.fromarray(stylized_photo)
        im.save(stylized_photo_path, 'JPEG')

    stylized_photo_filename = photo_filename(photo_hash, filter_name)
    return send_from_directory(PHOTOS_DIR, stylized_photo_filename)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
