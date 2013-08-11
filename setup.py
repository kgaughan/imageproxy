#!/usr/bin/env python

from setuptools import setup


setup(
    name='imageproxy',
    version='0.1.0',
    description='WSGI application to dynamically resize images.',
    long_description=open('README', 'r').read(),
    url='',
    license='Apache',
    py_modules=['imageproxy'],
    zip_safe=True,
    install_requires=[line.strip() for line in open('requirements.txt', 'r')],

    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ),

    author='Keith Gaughan',
    author_email='k@stereochro.me',
)
