from ConfigParser import ConfigParser


def get_config(config_file):
    config_obj = ConfigParser()
    config_obj.read(config_file)
    config = {}

    for section in config_obj.sections():
        for item in config_obj.items(section):
            val = item[1]
            try:
                config[section][item[0]] = val
            except KeyError:
                config[section] = {item[0]: val}

    return config


def open_file(path, mode, errormsg=None):
    try:
        return open(path, mode)
    except IOError as err:
        err.extra_info = errormsg
        raise
