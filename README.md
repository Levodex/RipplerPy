## About
* 
* (Read github/bitbucket description)

## Copyright notice

All parts of this project are under an attribution based MIT License by the author (See LICENSE.md)
The rippler code, the rippler logo and other rippler resources are intellectual properties of the author
'blowfish' is an intellectual property of Bruce Schneier
'zLib', 'trumbowyg', 'bootstrap' etc., are intellectual properties of their respective owners
Portions of this software use open-source libraries with sdifferent licenses (See ADDITIONAL LICENSES)

## Author

Ashutosh Verma
    <ashuto(dot)sh (at) outlook(dot)com>
    [https://levodex.com/, https://github.com/levodex]


## Install notes

* Make sure you have MongoDb set-up before running
* Install all additional wheels/eggs using WinPython before proceeding
* Give admin level access if you want Rippler running on http/https
      # Https mode is scheduled for the next release


## Release notes

* Do **NOT** package production builds with the zLib binaries present in the folder
    # This is a breaking change and on the TODO list: zLib code hasn't been merged in the project
    # And since base rippler was made in just 3 days it was left out for future versions
    # Use a portable zLib executable in the Ripple base directory/Install it on the side for your builds

* Secure Journalling is currently experimental and still in development
    # disable journalling before you package a production build


## Docs

Sadly I don't have enough time to write the docs right now but it is on the listed TODOs.
The code is pretty straightforward I think but if you want some brief detailing feel free to contact me and I'll explain :)


## License

[MIT © Ashutosh Verma](https://levodex.com/)
Read LICENSE.md and ADDITIONAL LICENSES
