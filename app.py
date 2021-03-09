#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, jsonify, request, send_file, make_response
from core.keys import Keyword as K
from core.core_service import CoreService
import uuid

dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

app = Flask(__name__, static_url_path='/static')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

@app.route('/')
@app.route('/upload.html')
def index_page():
    return render_template("upload.html")

@app.route('/install.html')
def install():
    return render_template("install.html")

@app.route('/new_ipa')
def new_ipa():
    return jsonify({
        K.result: K.ok,
        'file_id': str(uuid.uuid4())})

@app.route('/upload_ipa', methods = ['POST'])
def upload_ipa():
    file = request.files['new.ipa']
    file_id = request.args.get(K.fileId)
    save_path =  CoreService.temp_file(file_id)

    current_chunk = int(request.form['dzchunkindex'])

    try:
        with open(save_path, 'ab') as f:
            f.seek(int(request.form['dzchunkbyteoffset']))
            f.write(file.stream.read())
    except OSError:
        return make_response(("Not sure why, but we couldn't write the file to disk", 500))

    total_chunks = int(request.form['dztotalchunkcount'])

    if current_chunk + 1 == total_chunks:
        # This was the last chunk, the file should be complete and the size we expect
        if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
            return make_response(('Size mismatch', 500))

    return make_response(("Chunk upload successful", 200))

@app.route('/process_ipa')
def process_ipa():
    file_id = request.args.get(K.fileId)
    CoreService.process_ipa(file_id)

    install_url = '/install.html?id={0}'.format(file_id)
    return jsonify({
        K.result: K.ok,
        K.url: install_url
    })

@app.route('/app_info')
def app_info():
    app_id = request.args.get(K.id)
    app_info = CoreService.query_app(app_id)
    return jsonify(app_info)

@app.route('/manifest.plist')
def manifest():
    app_id = request.args.get(K.id)
    manifest = CoreService.gen_manifest(app_id)
    return manifest

@app.route('/app.ipa')
def app_ipa():
    app_id = request.args.get(K.id)
    ipa_path = CoreService.ipa_path(app_id)

    return send_file(ipa_path)

app.run(host='0.0.0.0', port=8086)
