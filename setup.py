from setuptools import setup, find_packages
from os import path

root_dir = path.abspath(path.dirname(__file__))

with open(path.join(root_dir, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="LinuxServerSetup-TirsvadCLI",
    version="0.3",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/orgs/Tirsvad-CLI-Tools/",
    author="Jens Tirsvad Nielsen",
    author_email="jenstirsvad@gmail.com",
    classifiers=[
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires='>=3.6, <4',
    install_requires=[
        'virtualenv',
        'PyYAML',
        'package-manager-TirsvadCLI>=0.1.11'
    ],
    extras_require = {
        'test': [
            'coverage',
            'pytest',
            'pytest-cov',
            'overalls',
            'PyYAML',
        ],
    },
)