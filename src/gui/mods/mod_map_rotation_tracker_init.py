from debug_utils import LOG_CURRENT_EXCEPTION


def init():
    try:
        from mod_map_rotation_tracker.server import g_map_rotation_server

        g_map_rotation_server.serve()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini():
    try:
        from mod_map_rotation_tracker.server import g_map_rotation_server

        g_map_rotation_server.close()
    except Exception:
        LOG_CURRENT_EXCEPTION()
