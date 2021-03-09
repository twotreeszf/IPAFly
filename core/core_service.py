# encoding: utf-8
"""
File:       core_service
Author:     twotrees.zf@gmail.com
Date:       2020年7月30日  31周星期四 10:55
Desc:
"""
import uuid
import os
from os import path
import zipfile
import plistlib
import re
import jsonpickle
from .keys import Keyword
import json
import subprocess

HOST_ORIGIN = 'https://ipafly.inkept.cn'

MANIFEST_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>items</key>
	<array>
		<dict>
			<key>assets</key>
			<array>
				<dict>
					<key>kind</key>
					<string>software-package</string>
					<key>url</key>
					<string>{ipa_url}</string>
				</dict>
			</array>
			<key>metadata</key>
			<dict>
				<key>bundle-identifier</key>
				<string>{bundle_id}</string>
				<key>bundle-version</key>
				<string>{app_version}</string>
				<key>kind</key>
				<string>software</string>
				<key>title</key>
				<string>{app_name}</string>
			</dict>
		</dict>
	</array>
</dict>
</plist>
'''

class IPAInfo:
    def __init__(self):
        self.bundle_id = ''
        self.app_name = ''
        self.app_version = ''
        self.icon_data = None

class CoreService:

    @classmethod
    def temp_file(cls, file_id):
        upload_folder = cls.upload_path()
        file_path = path.join(upload_folder, file_id)
        return file_path

    @classmethod
    def process_ipa(cls, file_id):
        file_path = path.join(cls.upload_path(), file_id)
        ipa_info = None
        try:
            ipa_info = cls.analyze_ipa(file_path)
        except Exception as e:
            print(e)
            os.remove(file_path)
            raise e

        # save ipa
        ipa_path = cls.ipa_path(file_id)
        os.rename(file_path, ipa_path)

        # save info
        info_path = cls.info_path(file_id)
        raw = jsonpickle.encode(ipa_info, indent=4)
        with open(info_path, 'w+') as f:
            f.write(raw)

    @classmethod
    def query_app(cls, app_id):
        app_info = None
        info_path = cls.info_path(app_id)
        with open(info_path) as f:
            app_info = json.loads(f.read())
            app_info['icon_data'] = app_info['icon_data']['py/b64']
        return app_info

    @classmethod
    def upload_path(cls):
        folder = os.getcwd()
        upload_folder = path.join(folder, 'upload')

        if not path.exists(upload_folder):
            os.mkdir(upload_folder)

        return upload_folder

    @classmethod
    def apps_path(cls):
        folder = os.getcwd()
        apps_folder = path.join(folder, 'apps')

        if not os.path.exists(apps_folder):
            os.mkdir(apps_folder)

        return apps_folder

    @classmethod
    def ipa_folder(cls, app_id):
        ipa_folder = os.path.join(cls.apps_path(), app_id)

        if not os.path.exists(ipa_folder):
            os.mkdir(ipa_folder)

        return ipa_folder

    @classmethod
    def ipa_path(cls, app_id):
        ipa_path = os.path.join(cls.ipa_folder(app_id), Keyword.app_ipa)
        return ipa_path

    @classmethod
    def info_path(cls, app_id):
        info_path = os.path.join(cls.ipa_folder(app_id), Keyword.info_json)
        return info_path

    @classmethod
    def analyze_ipa(cls, file_path):
        with zipfile.ZipFile(file_path) as ipa_file:
            plist_path = None
            name_list = ipa_file.namelist()
            pattern = re.compile(r'Payload/[^/]*.app/Info.plist')
            for path in name_list:
                m = pattern.match(path)
                if m is not None:
                    plist_path = m.group()
                    break

            plist_data = ipa_file.read(plist_path)
            plist_dic = plistlib.loads(plist_data)

            ipa = IPAInfo()
            ipa.bundle_id = plist_dic['CFBundleIdentifier']
            ipa.app_name = plist_dic['CFBundleDisplayName']
            ipa.app_version = plist_dic['CFBundleShortVersionString']

            main_icon_name = plist_dic['CFBundleIcons']['CFBundlePrimaryIcon']['CFBundleIconFiles'][-1]

            main_icon_path = None
            for path in name_list:
                file_name = os.path.basename(path)
                if file_name.startswith(main_icon_name):
                    main_icon_path = path
                    break
            icon_data = ipa_file.read(main_icon_path)
            icon_data = cls.normalize_png(icon_data)
            ipa.icon_data = icon_data

            return ipa

    @classmethod
    def normalize_png(cls, old_png):
        upload_folder = cls.upload_path()
        old_file = os.path.join(upload_folder, str(uuid.uuid4()))
        with open(old_file, 'wb') as f:
            f.write(old_png)

        new_file = os.path.join(upload_folder, str(uuid.uuid4()))

        cmd = 'xcrun pngcrush -revert-iphone-optimizations {0} {1}'.format(old_file, new_file)
        subprocess.check_output(cmd, shell=True).decode('utf-8')
        os.remove(old_file)
        if not os.path.exists(new_file):
            return None

        new_png = None
        with open(new_file, 'rb') as f:
             new_png = f.read()
        os.remove(new_file)

        return new_png

    @classmethod
    def gen_manifest(cls, app_id):
        appinfo = cls.query_app(app_id)
        version=appinfo['app_version']

        url = HOST_ORIGIN + '/app.ipa?id={0}'.format(app_id)
        manifest = MANIFEST_TEMPLATE.format(ipa_url=url, bundle_id=appinfo['bundle_id'], app_version=appinfo['app_version'], app_name=appinfo['app_name'])
        return manifest