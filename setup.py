#!/usr/bin/env python

from setuptools import setup


setup(
    name='imageproxy',
    version='0.1.0',
    description='WSGI application to dynamically resize images.',
    long_description=open('README', 'r').read(),
    url='https://github.com/kgaughan/imageproxy',
    license='Apache Licence v2.0',
    py_modules=['imageproxy'],
    zip_safe=True,
    install_requires=[line.strip() for line in open('requirements.txt', 'r')],

    entry_points={
        'paste.app_factory': (
            'main=imageproxy:create_application',
        ),
    },

    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ),

    author='Keith Gaughan',
    author_email='k@stereochro.me',
)
