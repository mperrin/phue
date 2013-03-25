



New Groups functionality:
---------------------------

You can create LightGroups by number or by name:

    >>> g = phue.LightGroup(b, 1)
    >>> hall = phue.LightGroup(b, 'Hallway')
    >>> office = phue.LightGroup(b, 'Office')


You can retrieve the lights in a LightGroup:

    >>> office.lights
    [<phue.Light object "Office 1" at 0x104963310>,
     <phue.Light object "Office 2" at 0x104963690>,
     <phue.Light object "Office 3" at 0x1049635d0>]

And you can change them:

    >>> office.lights = [1,2,3]
    DEBUG:phue:Setting lights in group 2 to [1, 2, 3]

        
