from debug_utils import LOG_CURRENT_EXCEPTION

g_map_rotation_server = None


def init():
    global g_map_rotation_server
    try:
        from mod_map_rotation_tracker.server import create_server

        g_map_rotation_server = create_server()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini():
    global g_map_rotation_server
    try:
        if g_map_rotation_server:
            g_map_rotation_server.close()
    except Exception:
        LOG_CURRENT_EXCEPTION()
