#!/usr/bin/env python


## TODO: DISCLAIMER, LICENSE, STUFF,...

import time

import rospy
import tf

from python_qt_binding.QtGui import QUndoCommand

from frame_editor.objects import *


class Command_SelectElement(QUndoCommand):

    def __init__(self, editor, element):
        QUndoCommand.__init__(self, "Select")
        self.editor = editor

        self.new_element = element
        self.old_element = editor.active_frame

    def redo(self):
        self.editor.active_frame = self.new_element
        self.editor.add_undo_level(2)

    def undo(self):
        self.editor.active_frame = self.old_element
        self.editor.add_undo_level(2)


class Command_AddElement(QUndoCommand):

    def __init__(self, editor, element):
        QUndoCommand.__init__(self, "Add")
        self.editor = editor

        self.element = element

    def redo(self):
        self.editor.frames[self.element.name] = self.element
        self.editor.add_undo_level(1)

    def undo(self):
        del self.editor.frames[self.element.name]
        self.editor.add_undo_level(1)


class Command_RemoveElement(QUndoCommand):

    def __init__(self, editor, element):
        QUndoCommand.__init__(self, "Remove")
        self.editor = editor

        self.element = element
        
        if editor.active_frame is element:
            self.was_active = True
        else:
            self.was_active = False

    def redo(self):
        if self.was_active:
            self.editor.active_frame = None
            self.editor.add_undo_level(2)

        del self.editor.frames[self.element.name]
        self.editor.add_undo_level(1)

    def undo(self):
        self.editor.frames[self.element.name] = self.element
        self.editor.add_undo_level(1)

        if self.was_active:
            self.editor.active_frame = self.element
            self.editor.add_undo_level(2)



class Command_ClearAll(QUndoCommand):

    def __init__(self, editor):
        QUndoCommand.__init__(self, "Clear all")
        self.editor = editor

        self.elements = editor.frames
        self.active_element = editor.active_frame

    def redo(self):
        self.editor.active_frame = None
        self.editor.frames = {}
        self.editor.add_undo_level(1+2)

    def undo(self):
        self.editor.active_frame = self.active_element
        self.editor.frames = self.elements
        self.editor.add_undo_level(1+2)


class Command_AlignElement(QUndoCommand):

    def __init__(self, editor, element, source_name, mode):
        QUndoCommand.__init__(self, "Align")
        self.editor = editor

        self.element = element

        self.old_position = element.position
        self.old_orientation = element.orientation

        ## New Pose ##
        ##
        (position, orientation) = element.listener.lookupTransform(element.parent, source_name, rospy.Time(0))

        ## Position
        pos = list(element.position)
        if "x" in mode:
            pos[0] = position[0]
        if "y" in mode:
            pos[1] = position[1]
        if "z" in mode:
            pos[2] = position[2]
        self.new_position = tuple(pos)

        ## Orientation
        rpy = list(tf.transformations.euler_from_quaternion(element.orientation))
        rpy_new = tf.transformations.euler_from_quaternion(orientation)
        if "a" in mode:
            rpy[0] = rpy_new[0]
        if "b" in mode:
            rpy[1] = rpy_new[1]
        if "c" in mode:
            rpy[2] = rpy_new[2]

        if "a" in mode or "b" in mode or "c" in mode:
            self.new_orientation = tf.transformations.quaternion_from_euler(*rpy)
        else:
            self.new_orientation = self.old_orientation

    def redo(self):
        self.element.position = self.new_position
        self.element.orientation = self.new_orientation
        self.element.broadcast()
        self.editor.add_undo_level(4)

    def undo(self):
        self.element.position = self.old_position
        self.element.orientation = self.old_orientation
        self.element.broadcast()
        self.editor.add_undo_level(4)


class Command_SetPose(QUndoCommand):

    def __init__(self, editor, element, position, orientation):
        QUndoCommand.__init__(self, "Position")
        self.editor = editor

        self.element = element

        self.time = time.time()

        self.new_position = position
        self.new_orientation = orientation
        self.old_position = element.position
        self.old_orientation = element.orientation

    def redo(self):
        self.element.position = self.new_position
        self.element.orientation = self.new_orientation
        self.element.broadcast()
        self.editor.add_undo_level(4)

    def undo(self):
        self.element.position = self.old_position
        self.element.orientation = self.old_orientation
        self.element.broadcast()
        self.editor.add_undo_level(4)

    def id(self):
        return 1

    def mergeWith(self, command):
        if self.id() != command.id():
            return False
        if self.element is not command.element:
            return False
        if time.time() - self.time > 1.0:
            return False # don't merge if too old

        ## Merge
        self.time = time.time()
        self.new_position = command.new_position
        self.new_orientation = command.new_orientation
        return True


class Command_SetPosition(QUndoCommand):

    def __init__(self, editor, element, position):
        QUndoCommand.__init__(self, "Position")
        self.editor = editor

        self.element = element

        self.new_position = position
        self.old_position = element.position

    def redo(self):
        self.element.position = self.new_position
        self.element.broadcast()
        self.editor.add_undo_level(4)

    def undo(self):
        self.element.position = self.old_position
        self.element.broadcast()
        self.editor.add_undo_level(4)


class Command_SetOrientation(QUndoCommand):

    def __init__(self, editor, element, orientation):
        QUndoCommand.__init__(self, "Orientation")
        self.editor = editor

        self.element = element

        self.new_orientation = orientation
        self.old_orientation = element.orientation

    def redo(self):
        self.element.orientation = self.new_orientation
        self.element.broadcast()
        self.editor.add_undo_level(4)

    def undo(self):
        self.element.orientation = self.old_orientation
        self.element.broadcast()
        self.editor.add_undo_level(4)


class Command_SetValue(QUndoCommand):

    def __init__(self, editor, element, symbol, value):
        QUndoCommand.__init__(self, "Value")
        self.editor = editor

        self.element = element
        self.symbol = symbol

        self.new_value = value
        self.old_value = element.value(symbol)

    def redo(self):
        self.element.set_value(self.symbol, self.new_value)
        self.element.broadcast()
        self.editor.add_undo_level(4)

    def undo(self):
        self.element.set_value(self.symbol, self.old_value)
        self.element.broadcast()
        self.editor.add_undo_level(4)


class Command_SetParent(QUndoCommand):

    def __init__(self, editor, element, parent_name, keep_absolute=True):
        QUndoCommand.__init__(self, "Parent")
        self.editor = editor

        self.element = element
        self.keep_absolute = keep_absolute

        self.new_parent_name = parent_name
        self.old_parent_name = element.parent

        if self.keep_absolute:
            (position, orientation) = element.listener.lookupTransform(parent_name, element.name, rospy.Time(0))
            self.new_position = position
            self.new_orientation = orientation

            self.old_position = element.position
            self.old_orientation = element.orientation

    def redo(self):
        self.element.parent = self.new_parent_name

        if self.keep_absolute:
            self.element.position = self.new_position
            self.element.orientation = self.new_orientation

        self.element.broadcast()
        self.editor.add_undo_level(4)

    def undo(self):
        self.element.parent = self.old_parent_name

        if self.keep_absolute:
            self.element.position = self.old_position
            self.element.orientation = self.old_orientation

        self.element.broadcast()
        self.editor.add_undo_level(4)



class Command_SetStyle(QUndoCommand):

    def __init__(self, editor, element, style):
        QUndoCommand.__init__(self, "Style")
        self.editor = editor

        self.old_element = element

        if style == "plane":
            self.new_element = Object_Plane(element.name, element.position, element.orientation, element.parent)
        elif style == "cube":
            self.new_element = Object_Cube(element.name, element.position, element.orientation, element.parent)
        elif style == "sphere":
            self.new_element = Object_Sphere(element.name, element.position, element.orientation, element.parent)
        elif style == "axis":
            self.new_element = Object_Axis(element.name, element.position, element.orientation, element.parent)
        else:
            self.new_element = Frame(element.name, element.position, element.orientation, element.parent)

        if editor.active_frame is element:
            self.was_active = True
        else:
            self.was_active = False

    def redo(self):
        del self.editor.frames[self.old_element.name]
        self.editor.frames[self.new_element.name] = self.new_element
        self.editor.add_undo_level(1+4)

        if self.was_active:
            self.editor.active_frame = self.new_element
            self.editor.add_undo_level(2)

    def undo(self):
        del self.editor.frames[self.new_element.name]
        self.editor.frames[self.old_element.name] = self.old_element
        self.editor.add_undo_level(1+4)

        if self.was_active:
            self.editor.active_frame = self.old_element
            self.editor.add_undo_level(2)


# eof