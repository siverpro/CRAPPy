# CRAPPy
CRyptocurrency Accounting Project Python

### Getting started
1. Run `docker build -t crap https://github.com/siverpro/CRAPPy.git`
2. copy the contents of [Example-conf.json](https://github.com/siverpro/CRAPPy/blob/master/conf-EXAMPLE.json), and make a new file called conf.json somewhere on your machine
3. Edit said file to fit your config and save it.
4. Run `docker run --rm -v LOCATION/OF/CONF.JSON:/app/CRAPPy/conf.json --name CRAP crap`

If all is well a progress bar should show up. 