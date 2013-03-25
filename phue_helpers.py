import phue

""" Misc helper/utility functions for use with phue.py

"""


def state(light):
    return "hue={0:d}, sat={1:d}, xy={2}, ct={3:d}".format(light.hue, light.saturation, light.xy, light.colortemp)


def delayed_off(delay=3600):
    """ Turn off all lights after some delay. """

    logger.info("Will turn off all lights in {0} s".format(delay))

    import time
    time.sleep(delay)
    b = Bridge()
    al = AllLights(b)
    al.on = False


