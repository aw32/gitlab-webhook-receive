import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gitlab-webhook-receive",
    version="0.0.1",
    author="",
    author_email="",
    description="Python server that receives Gitlab Webhook requests and executes commands",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aw32/gitlab-webhook-receive",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
    install_requires=[
    ],
)
