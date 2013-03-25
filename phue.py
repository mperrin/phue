#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
phue by Nathanaël Lécaudé - A Philips Hue Python library
Contributions by Marshall Perrin
https://github.com/studioimaginaire/phue
Original protocol hacking by rsmck : http://rsmck.co.uk/hue

Published under the GWTFPL - http://www.wtfpl.net

"Hue Personal Wireless Lighting" is a trademark owned by Koninklijke Philips Electronics N.V., see www.meethue.com for more information.
I am in no way affiliated with the Philips organization.

'''

import json
import os
import platform
import sys
if sys.version_info[0] > 2:
    PY3K = True
else:
    PY3K = False

if PY3K:
    import http.client as httplib
else:
    import httplib

import logging
logger = logging.getLogger('phue')
logging.basicConfig(level=logging.INFO)

if platform.system() == 'Windows':
    USER_HOME = 'USERPROFILE'
else:
    USER_HOME = 'HOME'


def _is_integer(somestring):
    try:
        int(somestring)
        return True
    except:
        return False


class Light(object):
    """ Hue Light object 
    
    Light settings can be accessed or set via the properties of this object.
    
    """
    def __init__(self, bridge, light_id):
        self.bridge = bridge
        self.light_id = light_id
        
        self._name = None
        self._on = None
        self._brightness = None
        self._colormode = None
        self._hue = None
        self._saturation = None
        self._xy = None
        self._colortemp = None
        self._alert = None
        self.transitiontime=None # default
        #self._reset_bri_after_on = False # see notes in 'on' function below
        self._reset_bri_after_on = None


    def __repr__(self):
        # like default python repr function, but add object name
        return '<%s.%s object "%s" at %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.name,
            hex(id(self))
        )

    # Wrapper functions for get/set through the bridge, adding support for
    # remembering the transitiontime parameter if the user has set it
    def _get(self, *args, **kwargs):
        return self.bridge.get_light(self.light_id, *args, **kwargs)
    def _set(self, *args, **kwargs):

        if self.transitiontime is not None:
            kwargs['transitiontime'] = self.transitiontime
            logger.debug("Setting with transitiontime = {0} ds = {1} s".format(self.transitiontime, float(self.transitiontime)/10))
            
            if args[0] == 'on' and args[1] == False:
                self._reset_bri_after_on = True
        return self.bridge.set_light(self.light_id, *args, **kwargs)
       
    @property
    def name(self):
        '''Get or set the name of the light [string]'''
        self._name = self._get('name')
        return self._name

    @name.setter
    def name(self, value):
        old_name = self.name
        self._name = value
        self._set('name', self._name)

        logger.debug("Renaming light from '{0}' to '{1}'".format(old_name, value))
        
        self.bridge.lights_by_name[self.name] = self 
        del self.bridge.lights_by_name[old_name]

    @property
    def on(self):
        '''Get or set the state of the light [True|False]'''
        self._on = self._get('on')
        return self._on

    @on.setter
    def on(self, value):

        # Some added code here to work around known bug where 
        # turning off with transitiontime set makes it restart on brightness = 1
        # see http://www.everyhue.com/vanilla/discussion/204/bug-with-brightness-when-requesting-ontrue-transitiontime5

        # if we're turning off, save whether this bug in the hardware has been invoked
        if self._on == True and value == False:
            self._reset_bri_after_on = self.transitiontime is not None
            if self._reset_bri_after_on: logger.warning('Turned off light with transitiontime specified, brightness will be reset on power on')

        self._set('on', value)

        # work around bug by resetting brightness after a power on
        if self._on == False and value == True:
            if self._reset_bri_after_on:
                logger.warning('Light was turned off with transitiontime specified, brightness needs to be reset now.')
                self.brightness = self._brightness
                self._reset_bri_after_on = False

        self._on = value

    @property
    def colormode(self):
        '''Get the color mode of the light [hue|xy|ct]'''
        self._colormode = self._get('colormode')
        return self._colormode
    
    @property
    def brightness(self):
        '''Get or set the brightness of the light [0-254]. 
        
        0 is not off'''
        
        self._brightness = self._get('bri')
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        self._brightness = value
        result = self._set('bri', self._brightness)

    bri = brightness # alias because I keep mis-typing this due to official hue API
    
    @property
    def hue(self):
        '''Get or set the hue of the light [0-65535]'''
        self._hue = self._get('hue')
        return self._hue

    @hue.setter
    def hue(self, value):
        self._hue = int(value) 
        self._set('hue', self._hue)

    @property
    def saturation(self):
        '''Get or set the saturation of the light [0-254]
        
        0 = white
        254 = most saturated
        '''
        self._saturation = self._get('sat')
        return self._saturation
    @saturation.setter
    def saturation(self, value):
        self._saturation = value
        self._set('sat', self._saturation)

    @property
    def xy(self):
        '''Get or set the color coordinates of the light [ [0.0-1.0, 0.0-1.0] ]
        
        This is in a color space similar to CIE 1931 (but not quite identical)
        '''
        self._xy = self._get('xy')
        return self._xy
    @xy.setter
    def xy(self, value):
        self._xy = value
        self._set('xy', self._xy)


    @property
    def colortemp(self):
        '''Get or set the color temperature of the light, in units of mireds [154-500]'''
        self._colortemp = self._get( 'ct')
        return self._colortemp
    @colortemp.setter
    def colortemp(self, value):
        if value < 154:
            logger.warn('154 mireds is coolest allowed color temp')
        elif value > 500:
            logger.warn('500 mireds is warmest allowed color temp')
        self._colortemp = value
        self._set('ct', self._colortemp)

    @property
    def colortemp_k(self):
        '''Get or set the color temperature of the light, in units of Kelvin [2000-6500]'''
        self._colortemp = self._get('ct')
        return int(round(1e6/self._colortemp))
    @colortemp_k.setter
    def colortemp_k(self, value):
        if value > 6500:
            logger.warn('6500 K is max allowed color temp')
            value = 6500
        elif value < 2000:
            logger.warn('2000 K is min allowed color temp')
            value = 2000
 
        colortemp_mireds = int(round(1e6/value))
        logger.debug("{0:d} K is {1} mireds".format(value, colortemp_mireds))
        self.colortemp = colortemp_mireds

 
    @property
    def alert(self):
        '''Get or set the alert state of the light [select|lselect|none]'''
        self._alert = self._get('alert')
        return self._alert
    @alert.setter
    def alert(self, value):
        if value is None: value = 'none'
        self._alert = value
        self._set('alert', self._alert)


    def get_rgb(self):
        """ Convert from native xyY colorspace to RGB
        Algorithm due to AaronH: 
            https://gist.github.com/AaronH/30c50aa4b161f8169c3d
        
        Note that this is far from a perfect conversion due to 
        color space limitations; see discussion at
        http://www.everyhue.com/vanilla/discussion/31/xy-colourspace/p1

        """
        X = self.xy[0]
        Y = self.xy[1]
        Z = 1-X-Y
        R =   3.233 * X - 1.5262 * Y + 0.2791 * Z
        G =  -0.8268* X + 2.4667 * Y + 0.3323 * Z
        B =  0.1294 * X + 0.1983 * Y + 2.0280 * Z

        return tuple(int(round(255*v)) for v in (R, G, B))
    def set_rgb(self,r,g,b):
        """ Attempt to set from RGB - 
        very imperfect color mapping
        see notes above for get_rgb
        """
        R = r/255.0
        G = g/255.0
        B = b/255.0

        X =  0.3739*R + 0.2386*G - 0.0906*B
        Y =  0.1303*R + 0.4940*G - 0.0989*B
        Z = -0.0366*R - 0.0635*G + 0.5085*B

        X = 0 if X < 0 else X
        Y = 0 if Y < 0 else Y

        return (X,Y)

    def set_color_by_name(self, colorname):
        """ Set based on human-readable color name
        Limited set implemented so far. 

        The color-name-to-hue mapping is of course pretty arbitrary, 
        this one is just based on that from the huepl Perl library
        """
        colortable= {'white':  {'hue': 0, 'sat': 0},
                      'red':    {'hue': 0, 'sat': 255},
                      'orange': {'hue': 4096, 'sat': 255},
                      'yellow': {'hue': 16384, 'sat': 255},
                      'green':  {'hue': 25600, 'sat': 255},
                      'blue':   {'hue': 47000, 'sat': 255},
                      'purple': {'hue': 49408, 'sat': 255},
                      'magenta':{'hue': 57344, 'sat': 255},
                      'pink':    {'hue': 0, 'sat': 128}}
        try:
            colorinfo = colortable[colorname]
        except:
            raise KeyError('{0} is not a defined color name.'.format(colorname))

        self._set(colorinfo)

class LightGroup(Light):
    """ A group of Hue lights, tracked as a group on the bridge """

    def __init__(self, bridge, group_id):
        Light.__init__(self, bridge, None)
        del self.light_id # not relevant for a group

        try:
            self.group_id = int(group_id)
        except:
            name = group_id
            groups = bridge.get_group()
            for idnumber, info in groups.items():
                if info['name'] == name: 
                    self.group_id = int(idnumber)
                    break
            else:
                raise LookupError("Could not find a group by that name.")
     


    # Wrapper functions for get/set through the bridge, adding support for
    # remembering the transitiontime parameter if the user has set it
    def _get(self, *args, **kwargs):
        return self.bridge.get_group(self.group_id, *args, **kwargs)
    def _set(self, *args, **kwargs):
        # let's get basic group functionality working first before adding transition time...
#        if self.transitiontime is not None:
#            kwargs['transitiontime'] = self.transitiontime
#            logger.debug("Setting with transitiontime = {0} ds = {1} s".format(self.transitiontime, float(self.transitiontime)/10))
#            
#            if args[0] == 'on' and args[1] == False:
#                self._reset_bri_after_on = True
        return self.bridge.set_group(self.group_id, *args, **kwargs)
       
    @property
    def name(self):
        '''Get or set the name of the light group [string]'''
        self._name = self._get('name')
        return self._name
    @name.setter
    def name(self, value):
        old_name = self.name
        logger.debug("Renaming light group from '{0}' to '{1}'".format(old_name, value))
        self._set('name', self._name)



    @property
    def lights(self):
        """ Return a list of all lights in this group"""
        #response = self.bridge.request('GET', '/api/{0}/groups/{1}'.format(self.bridge.username, self.group_id))
        #return [Light(self.bridge, int(l)) for l in response['lights']]
        return [Light(self.bridge, int(l)) for l in self._get('lights')]
    @lights.setter
    def lights(self, value):
        """ Change the lights that are in this group"""
        logger.debug("Setting lights in group {0} to {1}".format(self.group_id, str(value)))
        self._set('lights', value)



class AllLights(LightGroup):
    """ All the Hue lights connected to your bridge 
    
    This makes use of the semi-documented feature that 
    "Group 0" of lights appears to be a group automatically
    consisting of all lights.  This is not returned by 
    listing the groups, but is accessible if you explicitly
    ask for group 0. 
    """
    def __init__(self, bridge=None):
        if bridge==None: bridge=Bridge()
        LightGroup.__init__(self, bridge,0)
   
class Bridge(object):
    """ Interface to the Hue ZigBee bridge 
    
    You can obtain Light objects by calling the get_light_objects method:

        >>> b = Bridge(ip='192.168.1.100')
        >>> b.get_light_objects()
        [<phue.Light at 0x10473d750>,
         <phue.Light at 0x1046ce110>]

    Or more succinctly just by accessing this Bridge object as a list or dict:

        >>> b[0]
        <phue.Light at 0x10473d750>
        >>> b['Kitchen']
        <phue.Light at 0x1046ce110>


    
    """
    def __init__(self, ip = None, username = None, logging = 'info'):
        """ Initialization function. 

        Parameters:
        ------------
        ip : string
            IP address as dotted quad
        username : string, optional

        """
        self.set_logging(logging)

        if os.access(os.getenv(USER_HOME),os.W_OK):
            self.config_file_path = os.path.join(os.getenv(USER_HOME),'.python_hue')
        else:
            self.config_file_path = os.path.join(os.getcwd(),'.python_hue')

        self.ip = ip
        self.username = username
        self.lights_by_id = {}
        self.lights_by_name = {}
        self._name = None

        #self.minutes = 600
        #self.seconds = 10
        
        self.connect()
    
    def set_logging(self, level):
        if level == 'debug':
            logger.setLevel(logging.DEBUG)
        elif level == 'info':
            logger.setLevel(logging.INFO)
    
    @property
    def name(self):
        '''Get or set the name of the bridge [string]'''
        self._name = self.request('GET', '/api/' + self.username + '/config')['name']
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
        data = {'name' : self._name}
        self.request('PUT', '/api/' + self.username + '/config', json.dumps(data))

    def request(self,  mode = 'GET', address = None, data = None):
        connection = httplib.HTTPConnection(self.ip)
        if mode == 'GET' or mode == 'DELETE':
            connection.request(mode, address)
        if mode == 'PUT' or mode == 'POST':
            connection.request(mode, address, data)

        result = connection.getresponse()
        connection.close()
        if PY3K:
            return json.loads(str(result.read(), encoding='utf-8'))
        else:
            return json.loads(result.read())
    
    def register_app(self):
        registration_request = {"devicetype": "python_hue"}
        data = json.dumps(registration_request)
        response = self.request('POST', '/api', data)
        for line in response:
            for key in line:
                if 'success' in key:
                    with open(self.config_file_path, 'w') as f:
                        logger.info('Writing configuration file to ' + self.config_file_path)
                        f.write(json.dumps({self.ip : line['success']}))
                        logger.info('Reconnecting to the bridge')
                    self.connect()
                if 'error' in key:
                    if line['error']['type'] == 101:
                        logger.info('Please press button on bridge to register application and call connect() method')
                    if line['error']['type'] == 7:
                        logger.info('Unknown username')
    
    def connect(self):
        logger.info('Attempting to connect to the bridge...')
        # If the ip and username were provided at class init
        if self.ip is not None and self.username is not None:
            logger.info('Using ip: ' + self.ip)
            logger.info('Using username: ' + self.username)
            return
        
        if self.ip == None or self.username == None:
            try:
                with open(self.config_file_path) as f:
                    config = json.loads(f.read())
                    if self.ip is None:
                        self.ip = list(config.keys())[0]
                        logger.info('Using ip from config: ' + self.ip)
                    else:
                        logger.info('Using ip: ' + self.ip)
                    if self.username is None:
                        self.username =  config[self.ip]['username']
                        logger.info('Using username from config: ' + self.username)
                    else:
                        logger.info('Using username: ' + self.username)
            except Exception as e:
                logger.info('Error opening config file, will attempt bridge registration')
                self.register_app()

    def get_light_id_by_name(self,name):
        """ Lookup a light id based on string name. Case-sensitive. """
        lights = self.get_light()
        for light_id in lights:
            if PY3K:
                if name == lights[light_id]['name']:
                    return light_id
            else:
                if unicode(name, encoding='utf-8') == lights[light_id]['name']:
                    return light_id                
        return False

    def get_light_objects(self, mode = 'list'):
        """Returns a collection containing the lights, either by name or id (use 'id' or 'name' as the mode)
        The returned collection can be either a list (default), or a dict. 
        Set mode='id' for a dict by light ID, or mode='name' for a dict by light name.   """
        if self.lights_by_id == {}:
            lights = self.request('GET', '/api/' + self.username + '/lights/')
            for light in lights:
                self.lights_by_id[int(light)] = Light(self, int(light))
                self.lights_by_name[lights[light]['name']] = self.lights_by_id[int(light)]
        if mode == 'id':
            return self.lights_by_id
        if mode == 'name':
            return self.lights_by_name
        if mode == 'list':
            return [ self.lights_by_id[x] for x in range(1, len(self.lights_by_id) + 1) ]
  
    def __getitem__(self, key):
        """ Lights are accessibly by indexing the bridge either with 
        an integer index or string name. """
        if self.lights_by_id == {}:
            self.get_light_objects()

        try:
            return self.lights_by_id[key]
        except:
            try:
                return self.lights_by_name[key]
            except:
                raise KeyError('Not a valid key (integer index starting with 1, or light name): '+str(key))

    @property
    def lights(self):
        """ Access lights as a list """
        return self.get_light_objects(mode='list')

    def get_api(self):
        """ Returns the full api dictionary """
        return self.request('GET', '/api/' + self.username)

    def get_light(self, light_id = None, parameter = None):
        """ Gets state by light_id and parameter"""
        
        if PY3K:
            if type(light_id) == str:
                light_id = self.get_light_id_by_name(light_id)
        else:
            if type(light_id) == str or type(light_id) == unicode:
                light_id = self.get_light_id_by_name(light_id)
        if light_id == None:
            return self.request('GET', '/api/' + self.username + '/lights/' )
        state = self.request('GET', '/api/' + self.username + '/lights/' + str(light_id))
        if parameter == None:
            return state
        if parameter == 'name':
            return state[parameter]
        else:
            return state['state'][parameter]


    def set_light(self, light_id, parameter, value = None, transitiontime=None):
        """ Adjust properties of one or more lights. 

        light_id can be a single lamp or an array of lamps
        parameters: 'on' : True|False , 'bri' : 0-254, 'sat' : 0-254, 'ct': 154-500

        transitiontime : in **deciseconds**, time for this transition to take place
                         Note that transitiontime only applies to *this* light
                         command, it is not saved as a setting for use in the future!
                         Use the Light class' transitiontime attribute if you want
                         persistent time settings.

        """
        if type(parameter) == dict:
            data = parameter
        else:
            data = {parameter : value}

        if transitiontime is not None:
            data['transitiontime'] = int(round(transitiontime)) # must be int for request format

        light_id_array = light_id
        if PY3K:
            if type(light_id) == int or type(light_id) == str:
                light_id_array = [light_id]
        else:
            if type(light_id) == int or type(light_id) == str or type(light_id) == unicode:
                light_id_array = [light_id]            
        result = []
        for light in light_id_array:
            logger.debug(str(data))
            if parameter  == 'name':
                result.append(self.request('PUT', '/api/' + self.username + '/lights/'+ str(light_id), json.dumps(data)))
            else:
                if PY3K:
                    if type(light) == str:
                        converted_light = self.get_light_id_by_name(light)
                    else:
                        converted_light = light
                else:
                    if type(light) == str or type(light) == unicode:
                            converted_light = self.get_light_id_by_name(light)
                    else:
                        converted_light = light
                result.append(self.request('PUT', '/api/' + self.username + '/lights/'+ str(converted_light) + '/state', json.dumps(data)))
            if 'error' in list(result[-1][0].keys()):
                logger.warn("ERROR: {0} for light {1}".format(result[-1][0]['error']['description'], light) )

        logger.debug(result)
        return result

    ##### Groupt of lights #####
    @property
    def groups(self):
        """ Access groups as a list """
        return [LightGroup(self, groupid) for groupid in  self.get_group().keys()]
        
    
    def get_group(self, group_id = None, parameter = None):
        """ Get information for a group """
        if group_id == None:
            return self.request('GET', '/api/' + self.username + '/groups/')
        if parameter == None:
            return self.request('GET', '/api/' + self.username + '/groups/'+ str(group_id))
        elif parameter == 'name' or parameter == 'lights':
            return self.request('GET', '/api/' + self.username + '/groups/'+ str(group_id))[parameter]
        else:
            return self.request('GET', '/api/' + self.username + '/groups/'+  str(group_id))['action'][parameter]

    def set_group(self, group_id, parameter, value = None):
        """ Change light settings for a group 
        
        Parameters
        -----------

        """
        if type(parameter) == dict:
            data = parameter
        elif parameter == 'lights' and type(value) == list:
            data = {parameter : [str(x) for x in value] }
        else:
            data = {parameter : value}

        if parameter == 'name' or parameter == 'lights':
            return self.request('PUT', '/api/' + self.username + '/groups/'+ str(group_id), json.dumps(data))
        else:
            return self.request('PUT', '/api/' + self.username + '/groups/'+ str(group_id) + '/action', json.dumps(data))

    def create_group(self, name, lights = None):
        """ Create a group of lights

        Parameters
        ------------
        name : string
            Name for this group of lights
        lights : list
            List of lights to be in the group.

        """
        data = {'lights' : [str(x) for x in lights], 'name': name}
        return self.request('POST', '/api/' + self.username + '/groups/', json.dumps(data))

    def delete_group(self, group_id):
        return self.request('DELETE', '/api/' + self.username + '/groups/' + str(group_id))


    ##### Schedules #####
    @property
    def groups(self):
        """ Access groups as a list """
        return [LightGroup(self, groupid) for groupid in  self.get_group().keys()]
 
    def get_schedule(self, schedule_id = None, parameter = None):
        if schedule_id == None:
            return self.request('GET', '/api/' + self.username + '/schedules')
        if parameter == None:
            return self.request('GET', '/api/' + self.username + '/schedules/'+ str(schedule_id))

    def create_schedule(self, name, time, light_id, data, description = ' '):
        schedule = {
                    'name': name, 
                    'time': time, 
                    'description': description, 
                    'command':
                        {
                        'method': 'PUT', 
                        'address': '/api/' + self.username + '/lights/' + str(light_id) + '/state',
                        'body': data
                        }
                    }
        return self.request('POST', '/api/' + self.username + '/schedules', json.dumps(schedule))

    def create_group_schedule(self, name, time, group_id, data, description = ' '):
        schedule = {
                    'name': name, 
                    'time': time, 
                    'description': description, 
                    'command':
                        {
                        'method': 'PUT', 
                        'address': '/api/' + self.username + '/groups/' + str(group_id) + '/action',
                        'body': data
                        }
                    }
        return self.request('POST', '/api/' + self.username + '/schedules', json.dumps(schedule))

    def delete_schedule(self, schedule_id):
        return self.request('DELETE', '/api/' + self.username + '/schedules/' + str(schedule_id))


def state(light):
    return "hue={0:d}, sat={1:d}, xy={2}, ct={3:d}".format(light.hue, light.saturation, light.xy, light.colortemp)


def shutdown(delay=3600):
    logger.info("Will shutdown all lights in {0} s".format(delay))

    import time
    time.sleep(delay)
    b = Bridge()
    al = AllLights(b)
    al.on = False

if __name__ == '__main__':
    import argparse
    b = Bridge()

    parser = argparse.ArgumentParser()
    parser.add_argument('pos1', type=list)
    parser.add_argument('pos2')
    parser.add_argument('pos3')
    args = parser.parse_args()
    print(args.pos1)

'''
light 1 on
light 2 off


group 1 on
group 2 off

light Cuisine on
light Cuisine off

'''


