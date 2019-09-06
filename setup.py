import setuptools
#import os

#PROJECT_ROOT, _ = os.path.split(__file__)
REVISION = '0.0.1'
PROJECT_NAME = 'CzPubTran'
PROJECT_AUTHORS = "Václav Chaloupka"
PROJECT_EMAILS = 'vasek.chaloupka@hotmail.com'
PROJECT_URL = "https://github.com/bruxy70/CzPubTran"
SHORT_DESCRIPTION = 'Calling CHAPS REST API to get information about public transit in CZ'

setuptools.setup(
    name=PROJECT_NAME.lower(),
    version=REVISION,
    author=PROJECT_AUTHORS,
    author_email=PROJECT_EMAILS,
    packages=setuptools.find_packages(),
    url=PROJECT_URL,
    description=SHORT_DESCRIPTION,
    long_description_markdown_filename='README.md',  # uses setuptools-markdown
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Testing',
    ],
)
